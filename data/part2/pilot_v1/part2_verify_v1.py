"""Part 2 - Ask once, verify everywhere (research and due diligence).

The model gets three sources at once: the 10-Q (text), the earnings release
(text, a copy with two planted conflicts) and the earnings-call video (no
transcript). For each of 12 questions it returns a value, a conflict flag and
one citation per source that states the figure: a verbatim quote for documents,
a timestamp for the call.

Grading is by script (data/part2/answer_key.json):
  * value       within tolerance; the trap question is correct only if null
  * citations   document quotes must appear verbatim in the cited source and
                contain the expected figure; call timestamps must fall within
                30 s of where the figure is spoken
  * coverage    every source that states the figure is cited
  * conflicts   the two planted conflicts are flagged, with the release's
                (wrong) value cited, and no other question is flagged
A question is "fully verified" only if all four pass.

  python races/part2_verify.py --runs 5
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import common  # pylint: disable=g-import-not-at-top

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.path.join(ROOT, "data", "part2", "answer_key.json")
OUT = os.path.join(ROOT, "results", "part2_runs.jsonl")

SYSTEM = (
    "You are a due-diligence analyst. Use only the three sources provided. "
    "Never use outside knowledge. Every figure you report must be traceable to "
    "an exact place in a source."
)


def build_prompt(key: dict, docs: dict) -> str:
  lines = [
      "You have three sources about Alphabet's third quarter of 2026:",
      "  [10q]     the Form 10-Q (authoritative filing), text below",
      "  [release] the earnings release (Exhibit 99.1), text below",
      "  [call]    the earnings-call video (prepared remarks), attached",
      "",
      "The sources may disagree. If they do, the 10-Q is authoritative.",
      "",
      "For every question:",
      "- value: the figure in the units asked (negative numbers for losses or "
      "outflows), or null if no source states it.",
      "- conflict: true only if two sources state different figures for it "
      "(ignore rounding, e.g. 30,709 million vs $30.7 billion).",
      "- citations: one entry for EACH source that states the figure, with "
      "the value that source states:",
      '    documents: {"source": "10q" or "release", "quote": "<exact text '
      'copied from the source, 5-40 words, including the figure>", "value": '
      "<number>}",
      '    call: {"source": "call", "timestamp_s": <seconds from the start of '
      'the video where it is said>, "quote": "<what is said>", "value": '
      "<number>}",
      "  Copy document quotes character for character, including table rows "
      "as they appear. Do not cite a source that does not state the figure.",
      "",
      'Return only JSON: {"answers": {"<id>": {"value": ..., "conflict": ..., '
      '"citations": [...]}}}',
      "",
      "Questions:",
  ]
  for q in key["questions"]:
    lines.append(f'{q["id"]}: {q["question"]}')
  lines += [
      "",
      "=== [10q] ===",
      docs["10q"],
      "",
      "=== [release] ===",
      docs["release"],
  ]
  return "\n".join(lines)


_QUOTES = str.maketrans({"\u2019": "'", "\u2018": "'", "\u201c": '"',
                         "\u201d": '"', "\u2013": "-", "\u2014": "-",
                         "\u00a0": " "})


def norm(s: str) -> str:
  s = str(s).translate(_QUOTES).lower().replace("|", " ").replace("$", " ")
  return re.sub(r"\s+", " ", s).strip()


def quote_found(quote: str, doc_norm: str) -> bool:
  """Every fragment of the quote (split on ellipses) appears verbatim, in order."""
  frags = [f.strip(" .,;:\"'") for f in re.split(r"\.\.\.|\u2026", norm(quote))]
  frags = [f for f in frags if f]
  if not frags or sum(len(f) for f in frags) < 12:
    return False
  pos = 0
  for f in frags:
    i = doc_norm.find(f, pos)
    if i < 0:
      return False
    pos = i + len(f)
  return True


def to_float(x):
  if x is None or (isinstance(x, str) and x.strip().lower() in ("", "null", "none")):
    return None
  try:
    return float(str(x).replace(",", "").replace("$", "").replace("%", "").strip())
  except ValueError:
    return "bad"


def to_seconds(x):
  if isinstance(x, (int, float)):
    return float(x)
  m = re.fullmatch(r"\s*(?:(\d+):)?(\d+):(\d+(?:\.\d+)?)\s*", str(x or ""))
  if m:
    h, mi, s = m.groups()
    return int(h or 0) * 3600 + int(mi) * 60 + float(s)
  v = to_float(x)
  return v if isinstance(v, float) else None


def close(got, exp, q) -> bool:
  return isinstance(got, float) and abs(got - exp) <= max(abs(exp) * 0.005, q.get("abs_tol", 0))


def grade(answers: dict, key: dict, docs_norm: dict) -> dict:
  tol = key["call_tol_s"]
  totals = dict(value=0, conflict=0, coverage=0, cites=0, cites_ok=0,
                fully=0, conflicts_caught=0, false_conflicts=0)
  detail = {}
  for q in key["questions"]:
    a = answers.get(q["id"]) or {}
    got = to_float(a.get("value"))
    exp = q["answer"]
    value_ok = got is None if exp is None else close(got, exp, q)
    flagged = a.get("conflict") is True or str(a.get("conflict")).lower() == "true"
    cites = a.get("citations") or []
    checked, verified_sources = [], set()
    for c in cites:
      src = str(c.get("source", "")).lower().strip("[] ")
      ok, why = False, ""
      if src in ("10q", "release"):
        anchors = q["expect"].get(src)
        if not anchors:
          why = "source does not state this figure"
        elif not quote_found(c.get("quote", ""), docs_norm[src]):
          why = "quote not found verbatim"
        elif not any(all(norm(x) in norm(c.get("quote", "")) for x in s) for s in anchors):
          why = "quote does not contain the figure"
        else:
          ok = True
      elif src == "call":
        ref, ts = q["expect"].get("call"), to_seconds(c.get("timestamp_s"))
        if ref is None:
          why = "not said on the call"
        elif ts is None:
          why = "no timestamp"
        elif abs(ts - ref) > tol:
          why = f"timestamp {ts:.0f}s, said at {ref}s"
        else:
          ok = True
      else:
        why = "unknown source"
      if ok:
        verified_sources.add(src)
      checked.append({"source": src, "ok": ok, "why": why,
                      "value": c.get("value"), "timestamp_s": c.get("timestamp_s"),
                      "quote": str(c.get("quote", ""))[:300]})
    expected_sources = set(q["expect"])
    coverage_ok = expected_sources <= verified_sources
    cites_ok = all(c["ok"] for c in checked)
    if q.get("conflict"):
      p = q["planted"]
      planted_cited = any(c["ok"] and c["source"] == p["source"]
                          and close(to_float(c["value"]), p["value"], q) for c in checked)
      conflict_ok = flagged and planted_cited
      totals["conflicts_caught"] += conflict_ok
    else:
      conflict_ok = not flagged
      totals["false_conflicts"] += flagged
    fully = value_ok and conflict_ok and coverage_ok and cites_ok
    totals["value"] += value_ok
    totals["conflict"] += conflict_ok
    totals["coverage"] += coverage_ok
    totals["cites"] += len(checked)
    totals["cites_ok"] += sum(c["ok"] for c in checked)
    totals["fully"] += fully
    detail[q["id"]] = {"value": a.get("value"), "expected": exp, "value_ok": value_ok,
                       "conflict": flagged, "conflict_ok": conflict_ok,
                       "coverage_ok": coverage_ok, "missing_sources": sorted(expected_sources - verified_sources),
                       "fully_verified": fully, "citations": checked}
  n = len(key["questions"])
  return {
      "fully_verified": totals["fully"],
      "fully_verified_pct": round(100 * totals["fully"] / n, 1),
      "value_correct": totals["value"],
      "coverage_complete": totals["coverage"],
      "citations": totals["cites"],
      "citations_verified": totals["cites_ok"],
      "citation_precision_pct": round(100 * totals["cites_ok"] / max(totals["cites"], 1), 1),
      "conflicts_caught": totals["conflicts_caught"],
      "false_conflicts": totals["false_conflicts"],
      "accuracy_pct": round(100 * totals["fully"] / n, 1),
      "detail": detail,
  }


def load(key: dict) -> tuple[dict, dict]:
  docs = {s: open(os.path.join(ROOT, key["sources"][s]["file"]), encoding="utf-8").read()
          for s in ("10q", "release")}
  return docs, {s: norm(t) for s, t in docs.items()}


def run_one(model: str, thinking: str, run: int, key: dict, docs: dict, docs_norm: dict) -> dict:
  call = key["sources"]["call"]
  video = {
      "fileData": {"fileUri": call["video_url"], "mimeType": "video/*"},
      "videoMetadata": {"startOffset": call["start_offset"], "endOffset": call["end_offset"]},
  }
  res = common.generate(
      model,
      [video, {"text": build_prompt(key, docs)}],
      thinking=thinking,
      system=SYSTEM,
      json_mode=True,
      media_resolution="MEDIA_RESOLUTION_LOW",
  )
  row = {"race": "verify", "run": run, "ts": time.time(), **res.as_dict()}
  if res.error:
    row["grade"] = None
    return row
  try:
    parsed = common.parse_json(res.text)
    row["grade"] = grade(parsed.get("answers", parsed), key, docs_norm)
  except Exception as e:  # pylint: disable=broad-except
    row["grade"] = {"accuracy_pct": 0.0, "fully_verified": 0, "parse_error": repr(e)}
  return row


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--runs", type=int, default=5)
  ap.add_argument("--out", default=OUT)
  args = ap.parse_args()
  key = json.load(open(KEY, encoding="utf-8"))
  docs, docs_norm = load(key)

  def worker(cfg):
    model, thinking = cfg
    for r in range(args.runs):
      row = run_one(model, thinking, r, key, docs, docs_norm)
      common.append_jsonl(args.out, row)
      g = row.get("grade") or {}
      print(
          f"verify {model:18s} {thinking:5s} run{r} fully={g.get('fully_verified')}/12 "
          f"value={g.get('value_correct')} cites={g.get('citations_verified')}/{g.get('citations')} "
          f"conflicts={g.get('conflicts_caught')}/2 false={g.get('false_conflicts')} "
          f"t={row['seconds']}s ${row['cost_list_usd']:.4f} {row.get('error', '')[:80]}",
          flush=True,
      )

  with cf.ThreadPoolExecutor(len(common.CONFIGS)) as ex:
    list(ex.map(worker, common.CONFIGS))


if __name__ == "__main__":
  main()
