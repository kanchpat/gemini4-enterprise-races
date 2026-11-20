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


HINTS = {
    "401": "The OAuth token was rejected. Run `gcloud auth login` (and check "
           "`gcloud auth list` shows the right account), and `unset ACCESS_TOKEN` "
           "if you set it earlier. If you meant to use an AI Studio key, "
           "`unset GOOGLE_CLOUD_PROJECT` (it takes precedence over GEMINI_API_KEY).",
    "403": "The account lacks access. Enable the Vertex AI API on the project and "
           "give your account the Vertex AI User role, or use GEMINI_API_KEY.",
    "400": "If the message says the API key is invalid, create a new key at "
           "https://aistudio.google.com/apikey.",
    "404": "The model isn't available to this project or key. Try "
           "GOOGLE_CLOUD_LOCATION=global, or the other backend.",
}


def diagnose_token(common) -> None:
  """Says which token source was used and what Google thinks of the token."""
  import urllib.request  # pylint: disable=g-import-not-at-top
  if os.environ.get("ACCESS_TOKEN"):
    src = "ACCESS_TOKEN env var"
  elif os.environ.get("ACCESS_TOKEN_CMD"):
    src = f"ACCESS_TOKEN_CMD ({os.environ['ACCESS_TOKEN_CMD']})"
  else:
    src = "`gcloud auth print-access-token`"
  tok = common._token()  # pylint: disable=protected-access
  print(f"token source: {src}")
  print(f"token shape: {len(tok)} chars, starts with {tok[:5]!r} "
        f"(a valid OAuth token starts with 'ya29.'; extra lines or warnings break it)")
  try:
    with urllib.request.urlopen(
        "https://oauth2.googleapis.com/tokeninfo?access_token=" + tok, timeout=20) as r:
      info = json.load(r)
    print(f"tokeninfo: account={info.get('email', '?')} expires_in={info.get('expires_in')}s "
          f"scopes={info.get('scope', '')[:120]}")
  except Exception as e:  # pylint: disable=broad-except
    print(f"tokeninfo: Google does not recognise this token ({e}).")
  print()


def preflight() -> None:
  """One tiny call before spending money, with a clear fix if auth fails."""
  sys.path.insert(0, os.path.join(ROOT, "races"))
  import common  # pylint: disable=g-import-not-at-top
  if os.environ.get("GOOGLE_CLOUD_PROJECT"):
    print("backend: Vertex AI (GOOGLE_CLOUD_PROJECT is set; it overrides GEMINI_API_KEY)")
  else:
    print("backend: Gemini API (GEMINI_API_KEY)")
  res = common.generate("gemini-4-hydrogen", [{"text": "Reply with OK."}],
                        thinking="LOW", max_output_tokens=256, retries=0)
  if res.error:
    code = res.error.split()[1].rstrip(":") if res.error.startswith("HTTP") else ""
    print(f"\nPreflight call failed: {res.error}\n")
    if code == "401" and os.environ.get("GOOGLE_CLOUD_PROJECT"):
      diagnose_token(common)
    sys.exit("Fix: " + HINTS.get(code, "check your credentials and network."))
  print("preflight OK: gemini-4-hydrogen answered\n")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--runs", type=int, default=1)
  ap.add_argument("--out-dir", default=None)
  args = ap.parse_args()

  if not (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_CLOUD_PROJECT")):
    sys.exit("Set GEMINI_API_KEY or GOOGLE_CLOUD_PROJECT first (see README > Installation).")

  preflight()
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
