"""Race 1 - Analyst: answer 25 finance questions from Alphabet's Q3 2026 10-Q.

Every model gets the same 10-Q text and the same prompt, and must return one
JSON object. Answers are graded by script against an answer key built from the
filing's own XBRL facts (SEC inline XBRL), so no human or model judges the
headline numbers.

  python races/race1_analyst.py --runs 5
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
DOC = os.path.join(ROOT, "data", "race1", "goog-10q-2026q3.txt")
KEY = os.path.join(ROOT, "data", "race1", "answer_key.json")
OUT = os.path.join(ROOT, "results", "race1_runs.jsonl")

SYSTEM = (
    "You are a senior equity research analyst. Work only from the filing you "
    "are given. Never estimate or use outside knowledge. If a value is not in "
    "the filing and cannot be computed from it, answer null."
)


def build_prompt(questions: list[dict]) -> str:
  lines = [
      "Below is Alphabet Inc.'s Form 10-Q for the quarter ended September 30, "
      "2026, converted to plain text from the SEC filing.",
      "",
      "Answer every question. Rules:",
      "- Dollar amounts in USD millions (e.g. 1,234.5 million -> 1234.5).",
      "- Per-share amounts in USD (e.g. 2.12).",
      "- Percentages as a number of percent, rounded to 2 decimals "
      "(e.g. 24.65 for 24.65%).",
      "- Losses, outflows and negative changes are negative numbers.",
      "- Return only a JSON object mapping each question id to a number "
      "or null. No other text.",
      "",
      "Questions:",
  ]
  for q in questions:
    lines.append(f'{q["id"]}: {q["question"]}')
  return "\n".join(lines)


def grade(answers: dict, questions: list[dict]) -> dict:
  correct, wrong, missing, detail = 0, 0, 0, {}
  for q in questions:
    got = answers.get(q["id"])
    exp = q["answer"]
    if exp is None:  # trap question: the only right answer is null
      ok = got is None or str(got).strip().lower() in ("", "null", "none")
      correct += ok
      wrong += not ok
      detail[q["id"]] = {"got": got, "expected": None, "ok": ok}
      continue
    if got is None or got == "":
      missing += 1
      detail[q["id"]] = {"got": None, "expected": exp, "ok": False}
      continue
    try:
      g = float(str(got).replace(",", "").replace("%", "").replace("$", ""))
    except ValueError:
      wrong += 1
      detail[q["id"]] = {"got": got, "expected": exp, "ok": False}
      continue
    if q["unit"] == "pct":
      ok = abs(g - exp) <= 0.15
    else:
      ok = abs(g - exp) <= max(abs(exp) * 0.005, 0.01)
    correct += ok
    wrong += not ok
    detail[q["id"]] = {"got": g, "expected": exp, "ok": ok}
  n = len(questions)
  return {
      "accuracy_pct": round(100 * correct / n, 1),
      "correct": correct,
      "wrong_values": wrong,  # confident but wrong: the costly kind
      "missing": missing,
      "detail": detail,
  }


def run_one(model: str, thinking: str, run: int, doc: str, key: dict) -> dict:
  prompt = build_prompt(key["questions"])
  res = common.generate(
      model,
      [{"text": doc}, {"text": prompt}],
      thinking=thinking,
      system=SYSTEM,
      json_mode=True,
  )
  row = {"race": "analyst", "run": run, "ts": time.time(), **res.as_dict()}
  if res.error:
    row["grade"] = None
    return row
  try:
    answers = common.parse_json(res.text)
  except Exception as e:  # pylint: disable=broad-except
    row["grade"] = {"accuracy_pct": 0.0, "parse_error": repr(e)}
    return row
  row["grade"] = grade(answers, key["questions"])
  return row


def main() -> None:
  ap = argparse.ArgumentParser()
  ap.add_argument("--runs", type=int, default=5)
  ap.add_argument("--out", default=OUT)
  args = ap.parse_args()
  doc = open(DOC, encoding="utf-8").read()
  key = json.load(open(KEY, encoding="utf-8"))

  def worker(cfg):
    model, thinking = cfg
    for r in range(args.runs):
      row = run_one(model, thinking, r, doc, key)
      common.append_jsonl(args.out, row)
      g = row.get("grade") or {}
      print(
          f"{model:18s} {thinking:5s} run{r} acc={g.get('accuracy_pct')} "
          f"wrong={g.get('wrong_values')} t={row['seconds']}s "
          f"${row['cost_list_usd']:.4f} {row.get('error','')[:80]}",
          flush=True,
      )

  # Configs run side by side; runs within a config run one after another.
  with cf.ThreadPoolExecutor(len(common.CONFIGS)) as ex:
    list(ex.map(worker, common.CONFIGS))


if __name__ == "__main__":
  main()
