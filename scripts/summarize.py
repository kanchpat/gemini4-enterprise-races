#!/usr/bin/env python3
"""Summarize race runs into results/summary.json (medians and ranges).

Standard library only. Usage:
  python3 scripts/summarize.py            # writes results/summary.json
  python3 scripts/summarize.py --print    # also prints a Markdown table
"""

from __future__ import annotations

import argparse
import json
import os
import statistics

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Test id -> (results file, enterprise use case label).
TESTS = {
    "analyst": ("results/race1_runs.jsonl", "Financial reporting analysis"),
    "intake": ("results/race2_runs.jsonl", "Meeting and call intelligence"),
    "audit": ("results/audit_runs.jsonl", "Review and controls"),
    "ladder_pilot": ("results/pilot/ladder.jsonl", "Multi-step reasoning (pilot, 1 run)"),
}

LABELS = {
    ("gemini-4-hydrogen", "LOW"): "Gemini 4 Hydrogen (low)",
    ("gemini-4-hydrogen", "HIGH"): "Gemini 4 Hydrogen (high)",
    ("gemini-3.8-flash", "HIGH"): "Gemini 3.8 Flash (high)",
    ("gemini-4-neon", "HIGH"): "Gemini 4 Neon (high)",
    ("gemini-4-neon", "XHIGH"): "Gemini 4 Neon (extra high)",
}


def _load(path: str) -> list[dict]:
  with open(os.path.join(ROOT, path)) as f:
    return [json.loads(line) for line in f if line.strip()]


def summarize(run_dir: str | None = None) -> dict:
  out = {"tests": {}}
  for test, (path, use_case) in TESTS.items():
    if run_dir:
      if test == "ladder_pilot":
        continue
      path = os.path.relpath(os.path.join(run_dir, f"{test}.jsonl"), ROOT)
    groups: dict[tuple, list[dict]] = {}
    for r in _load(path):
      if r.get("error"):
        continue
      groups.setdefault((r["model"], r["thinking"]), []).append(r)
    configs = []
    for (model, thinking), rows in groups.items():
      acc = [r["grade"]["accuracy_pct"] for r in rows]
      secs = [r["seconds"] for r in rows]
      usd = [r["cost_list_usd"] for r in rows]
      row = {
          "model": model,
          "thinking": thinking,
          "label": LABELS.get((model, thinking), f"{model} ({thinking})"),
          "runs": len(rows),
          "accuracy_median_pct": statistics.median(acc),
          "accuracy_min_pct": min(acc),
          "accuracy_max_pct": max(acc),
          "seconds_median": round(statistics.median(secs), 1),
          "seconds_min": round(min(secs), 1),
          "seconds_max": round(max(secs), 1),
          "cost_usd_median": round(statistics.median(usd), 4),
      }
      if test == "audit":
        found = sum(len(r["grade"]["found"]) for r in rows)
        total = found + sum(len(r["grade"]["missed"]) for r in rows)
        row["errors_found"] = found
        row["errors_planted"] = total
        row["false_flags"] = sum(r["grade"]["false_flags"] for r in rows)
        missed: dict[str, int] = {}
        for r in rows:
          for e in r["grade"]["missed"]:
            eid = e if isinstance(e, str) else e.get("id", str(e))
            missed[eid] = missed.get(eid, 0) + 1
        row["missed_by_error"] = missed
      configs.append(row)
    configs.sort(key=lambda c: c["seconds_median"])
    out["tests"][test] = {"use_case": use_case, "source": path,
                          "configs": configs}
  return out


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--print", action="store_true", help="print Markdown table")
  ap.add_argument("--dir", default=None,
                  help="summarize a run folder from scripts/run_all.py instead")
  args = ap.parse_args()
  summary = summarize(args.dir)
  dest = (os.path.join(args.dir, "summary.json") if args.dir
          else os.path.join(ROOT, "results", "summary.json"))
  with open(dest, "w") as f:
    json.dump(summary, f, indent=2)
  print(f"wrote {os.path.relpath(dest, ROOT)}")
  if args.print:
    for test, t in summary["tests"].items():
      print(f"\n### {test}: {t['use_case']}\n")
      print("| Setup | Runs | Accuracy (median) | Time (median) | Cost (median) |")
      print("|---|---|---|---|---|")
      for c in t["configs"]:
        acc = f"{c['accuracy_median_pct']:.0f}%"
        if "errors_found" in c:
          acc = f"{c['errors_found']}/{c['errors_planted']} errors"
        print(f"| {c['label']} | {c['runs']} | {acc} | "
              f"{c['seconds_median']:.0f} s | ${c['cost_usd_median']:.3f} |")


if __name__ == "__main__":
  main()
