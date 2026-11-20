#!/usr/bin/env python3
"""Run all three Part 1 tests in one go and save the runs to their own folder.

Standard library only. Usage:
  python3 scripts/run_all.py                 # 1 run per setup (~$4 at list price)
  python3 scripts/run_all.py --runs 5        # full 5-run pass (~$19)
  python3 scripts/run_all.py --out-dir results/verification/my-run

Each test writes one JSON line per model call to <out-dir>/<test>.jsonl,
including the API's receipt fields (response_id, model_version, create_time).
At the end it prints a summary table and a receipts table.
"""

import argparse
import datetime
import json
import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TESTS = [
    ("analyst", "Financial reporting analysis", ["races/race1_analyst.py"]),
    ("intake", "Meeting and call intelligence", ["races/race2_intake.py"]),
    ("audit", "Review and controls", ["races/race_hard.py", "--task", "audit"]),
]


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--runs", type=int, default=1)
  ap.add_argument("--out-dir", default=None)
  args = ap.parse_args()

  if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_CLOUD_PROJECT")):
    sys.exit("Set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT first (see README > Installation).")

  stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%MZ")
  out_dir = args.out_dir or os.path.join(ROOT, "results", "verification", stamp)
  os.makedirs(out_dir, exist_ok=True)
  backend = "Vertex AI" if os.environ.get("GOOGLE_CLOUD_PROJECT") else "Gemini API"
  print(f"== Gemini for Real-Life Enterprise Use Cases · Part 1 ==")
  print(f"started {stamp} · backend {backend} · {args.runs} run(s) per setup")
  print(f"writing to {os.path.relpath(out_dir, ROOT)}\n")

  for test, use_case, cmd in TESTS:
    out = os.path.join(out_dir, f"{test}.jsonl")
    print(f"-- Enterprise use case: {use_case} ({test}) --", flush=True)
    t0 = time.monotonic()
    subprocess.run([sys.executable, *cmd, "--runs", str(args.runs), "--out", out],
                   cwd=ROOT, check=True)
    print(f"   done in {time.monotonic() - t0:.0f} s\n", flush=True)

  subprocess.run([sys.executable, "scripts/summarize.py", "--dir", out_dir, "--print"],
                 cwd=ROOT, check=True)

  print("\n### Receipts (from the API response)\n")
  print("| Test | Setup | Run | response_id | model_version | create_time |")
  print("|---|---|---|---|---|---|")
  for test, _, _ in TESTS:
    with open(os.path.join(out_dir, f"{test}.jsonl")) as f:
      for line in f:
        r = json.loads(line)
        x = r.get("extra") or {}
        print(f"| {test} | {r['model']} ({r['thinking']}) | {r['run']} | "
              f"{x.get('response_id', '')} | {x.get('model_version', '')} | "
              f"{x.get('create_time', '')} |")


if __name__ == "__main__":
  main()
