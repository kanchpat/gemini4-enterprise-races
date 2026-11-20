"""Hard rungs: (a) audit a 10-Q with six planted errors, (b) multi-step ladder.

  python races/race_hard.py --task audit  --runs 5
  python races/race_hard.py --task ladder --runs 5

audit:  the model gets the real 10-Q with six planted inconsistencies and must
        list every inconsistency it can prove from the document. Graded by
        matching the reported wrong value to each planted value; anything that
        matches no planted error counts as a false flag.
ladder: 16 questions that need figures combined across sections (implied
        first-half numbers, margin changes, reconciliations) plus two trap
        questions whose only correct answer is null. Graded like race 1.
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import common  # pylint: disable=g-import-not-at-top
import race1_analyst  # pylint: disable=g-import-not-at-top

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

AUDIT_DOC = os.path.join(ROOT, "data", "audit", "goog-10q-2026q3-planted.txt")
AUDIT_KEY = os.path.join(ROOT, "data", "audit", "planted_errors.json")
LADDER_DOC = os.path.join(ROOT, "data", "race1", "goog-10q-2026q3.txt")
LADDER_KEY = os.path.join(ROOT, "data", "ladder", "answer_key.json")

HARD_CONFIGS = list(common.CONFIGS)  # add Neon XHIGH with --xhigh

AUDIT_PROMPT = """You are auditing the Form 10-Q above before it is filed.
Someone may have introduced numeric errors. Find every figure that is
internally inconsistent with the rest of THIS document: a table row that does
not match the same figure elsewhere, totals that do not add up, a stated
growth rate or change that does not match the underlying numbers, a part that
exceeds its whole, and so on.

Report only inconsistencies you can prove from the document itself. Do not
flag rounding differences of less than 0.5%, judgement calls, or anything that
needs outside knowledge. A false flag costs as much as a missed error.

Return only JSON:
{"findings": [{"quote": "<short exact text containing the wrong figure>",
  "wrong_value": <the incorrect number exactly as written, e.g. 113 for 113%>,
  "correct_value": <what it should be, as a number>,
  "proof": "<one sentence>"}]}
"""


def _num(x):
  try:
    return float(str(x).replace(",", "").replace("%", "").replace("$", ""))
  except (TypeError, ValueError):
    return None


def grade_audit(findings: list[dict], key: dict) -> dict:
  found, false_flags, matched = set(), 0, []
  for f in findings:
    w = _num(f.get("wrong_value"))
    hit = None
    if w is not None:
      for e in key["errors"]:
        if e["id"] in found:
          continue
        cands = [e["wrong_value"]] + e.get("alt_values", [])
        if any(abs(w - pw * s) <= abs(pw * s) * 0.005
               for pw in cands for s in (1, 1000, 0.001)):
          hit = e["id"]
          break
    if hit:
      found.add(hit)
      matched.append(hit)
    else:
      false_flags += 1
  n = len(key["errors"])
  return {
      "accuracy_pct": round(100 * len(found) / n, 1),
      "found": sorted(found),
      "missed": sorted(e["id"] for e in key["errors"] if e["id"] not in found),
      "false_flags": false_flags,
      "n_findings": len(findings),
  }


def run_one(task: str, model: str, thinking: str, run: int, doc: str, key: dict):
  if task == "audit":
    parts = [{"text": doc}, {"text": AUDIT_PROMPT}]
    system = "You are a meticulous financial-statement auditor."
  else:
    parts = [{"text": doc}, {"text": race1_analyst.build_prompt(key["questions"])}]
    system = race1_analyst.SYSTEM
  res = common.generate(model, parts, thinking=thinking, system=system,
                        json_mode=True, max_output_tokens=65536)
  row = {"race": task, "run": run, "ts": time.time(), **res.as_dict()}
  if res.error:
    row["grade"] = None
    return row
  try:
    out = common.parse_json(res.text)
    if task == "audit":
      row["grade"] = grade_audit(out.get("findings", []), key)
    else:
      row["grade"] = race1_analyst.grade(out, key["questions"])
  except Exception as e:  # pylint: disable=broad-except
    row["grade"] = {"accuracy_pct": 0.0, "parse_error": repr(e)}
  return row


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--task", choices=["audit", "ladder"], required=True)
  ap.add_argument("--runs", type=int, default=5)
  ap.add_argument("--out", default=None)
  ap.add_argument("--xhigh", action="store_true",
                  help="also run Neon at XHIGH (needs a large output cap)")
  args = ap.parse_args()
  configs = HARD_CONFIGS + ([("gemini-4-neon", "XHIGH")] if args.xhigh else [])
  doc_path, key_path = (
      (AUDIT_DOC, AUDIT_KEY) if args.task == "audit" else (LADDER_DOC, LADDER_KEY)
  )
  doc = open(doc_path, encoding="utf-8").read()
  key = json.load(open(key_path, encoding="utf-8"))
  out = args.out or os.path.join(ROOT, "results", f"{args.task}_runs.jsonl")

  def worker(cfg):
    model, thinking = cfg
    for r in range(args.runs):
      row = run_one(args.task, model, thinking, r, doc, key)
      common.append_jsonl(out, row)
      g = row.get("grade") or {}
      print(
          f"{args.task} {model:18s} {thinking:5s} run{r} "
          f"acc={g.get('accuracy_pct')} ff={g.get('false_flags')} "
          f"wrong={g.get('wrong_values')} missed={g.get('missed')} "
          f"t={row['seconds']}s ${row['cost_list_usd']:.4f} "
          f"{row.get('error','')[:80]}",
          flush=True,
      )

  with cf.ThreadPoolExecutor(len(configs)) as ex:
    list(ex.map(worker, configs))


if __name__ == "__main__":
  main()
