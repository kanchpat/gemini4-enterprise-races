#!/usr/bin/env python3
"""Build the single-file site: site/src/* + results/summary.json -> docs/index.html.

Standard library only. Usage:
  python3 scripts/build_site.py
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "site", "src")


def _read(*parts: str) -> str:
  with open(os.path.join(ROOT, *parts), encoding="utf-8") as f:
    return f.read()


def main() -> None:
  summary = json.loads(_read("results", "summary.json"))
  # Drop large per-error maps the page doesn't need; keep it compact.
  data = json.dumps(summary, separators=(",", ":")).replace("</", "<\\/")
  js = _read("site", "src", "app.js").replace("/*DATA*/null", data, 1)
  html = _read("site", "src", "index.tpl.html")
  html = html.replace("/*CSS*/", _read("site", "src", "style.css"), 1)
  html = html.replace("/*JS*/", js, 1)
  dest = os.path.join(ROOT, "docs", "index.html")
  with open(dest, "w", encoding="utf-8") as f:
    f.write(html)
  print(f"wrote docs/index.html ({len(html):,} bytes)")


if __name__ == "__main__":
  main()
