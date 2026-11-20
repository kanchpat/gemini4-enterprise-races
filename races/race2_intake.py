"""Race 2 - Intake: pull 20 facts straight from a recorded earnings call video.

Input is the public YouTube recording of Alphabet's Q3 2026 earnings call
(prepared remarks, 0:00-33:46, about 200k video tokens at low media
resolution). There is no transcript and no slide text: the model must listen.
Answers are graded by script. Most answers are cross-checked against the
SEC filings; the rest are spoken-only figures (see data/race2/answer_key.json).

  python races/race2_intake.py --runs 5
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

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KEY = os.path.join(ROOT, "data", "race2", "answer_key.json")
OUT = os.path.join(ROOT, "results", "race2_runs.jsonl")

SYSTEM = (
    "You are an investor-relations analyst. Use only what is said or shown in "
    "the recording. Never use outside knowledge. If something is not said or "
    "shown in the recording, answer null."
)


def build_prompt(questions: list[dict]) -> str:
  lines = [
      "The video is the recording of Alphabet's Q3 2026 earnings call "
      "(prepared remarks). Answer every question from the recording.",
      "",
      "Rules:",
      "- Use the units given in each question.",
      "- Use the figure as stated on the call (e.g. 'up 25%' -> 25).",
      "- Negative values are negative numbers.",
      "- Return only a JSON object mapping each question id to a number or "
      "null. No other text.",
      "",
      "Questions:",
  ]
  for q in questions:
    lines.append(f'{q["id"]}: {q["question"]}')
  return "\n".join(lines)


def grade(answers: dict, questions: list[dict]) -> dict:
  correct, wrong, missing, detail = 0, 0, 0, {}
  for q in questions:
    got, exp = answers.get(q["id"]), q["answer"]
    if exp is None:
      ok = got is None or str(got).strip().lower() in ("", "null", "none")
    elif got is None or got == "":
      missing += 1
      detail[q["id"]] = {"got": None, "expected": exp, "ok": False}
      continue
    else:
      try:
        g = float(str(got).replace(",", "").replace("%", "").replace("$", ""))
        got = g
        ok = abs(g - exp) <= max(abs(exp) * 0.01, q.get("abs_tol", 0.0))
      except ValueError:
        ok = False
    correct += ok
    wrong += not ok
    detail[q["id"]] = {"got": got, "expected": exp, "ok": ok}
  return {
      "accuracy_pct": round(100 * correct / len(questions), 1),
      "correct": correct,
      "wrong_values": wrong,
      "missing": missing,
      "detail": detail,
  }


def run_one(model: str, thinking: str, run: int, key: dict) -> dict:
  video = {
      "fileData": {"fileUri": key["video_url"], "mimeType": "video/*"},
      "videoMetadata": {
          "startOffset": key["start_offset"],
          "endOffset": key["end_offset"],
      },
  }
  res = common.generate(
      model,
      [video, {"text": build_prompt(key["questions"])}],
      thinking=thinking,
      system=SYSTEM,
      json_mode=True,
      media_resolution="MEDIA_RESOLUTION_LOW",
  )
  row = {"race": "intake", "run": run, "ts": time.time(), **res.as_dict()}
  if res.error:
    row["grade"] = None
    return row
  try:
    row["grade"] = grade(common.parse_json(res.text), key["questions"])
  except Exception as e:  # pylint: disable=broad-except
    row["grade"] = {"accuracy_pct": 0.0, "parse_error": repr(e)}
  return row


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--runs", type=int, default=5)
  ap.add_argument("--out", default=OUT)
  args = ap.parse_args()
  key = json.load(open(KEY, encoding="utf-8"))

  def worker(cfg):
    model, thinking = cfg
    for r in range(args.runs):
      row = run_one(model, thinking, r, key)
      common.append_jsonl(args.out, row)
      g = row.get("grade") or {}
      print(
          f"{model:18s} {thinking:5s} run{r} acc={g.get('accuracy_pct')} "
          f"wrong={g.get('wrong_values')} t={row['seconds']}s "
          f"${row['cost_list_usd']:.4f} {row.get('error','')[:80]}",
          flush=True,
      )

  with cf.ThreadPoolExecutor(len(common.CONFIGS)) as ex:
    list(ex.map(worker, common.CONFIGS))


if __name__ == "__main__":
  main()
