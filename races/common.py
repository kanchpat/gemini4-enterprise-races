"""Shared helpers: model calls, timing, token accounting and list-price cost.

Works against either backend with the same request shape:
  * Vertex AI   -> set GOOGLE_CLOUD_PROJECT (auth: ACCESS_TOKEN env var or
                   `gcloud auth print-access-token`)
  * Gemini API  -> set GEMINI_API_KEY
Only the Python standard library is used here.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field

# Public list prices, USD per 1M tokens (ai.google.dev/gemini-api/docs/pricing,
# checked 2026-11-20). Output price includes thinking tokens.
PRICES = {
    "gemini-4-neon": {"in": 3.00, "out": 15.00, "cached": 0.15},
    "gemini-4-hydrogen": {"in": 1.50, "out": 7.50, "cached": 0.075},
    # Promotional rate through 2026-12-31 ($1.50 / $7.50 from 2027-01-01).
    "gemini-3.8-flash": {"in": 0.75, "out": 3.75, "cached": 0.075},
}

DISPLAY = {
    "gemini-4-neon": "Gemini 4 Neon",
    "gemini-4-hydrogen": "Gemini 4 Hydrogen",
    "gemini-3.8-flash": "Gemini 3.8 Flash",
}


@dataclass
class CallResult:
  model: str
  thinking: str
  text: str
  seconds: float
  prompt_tokens: int = 0
  cached_tokens: int = 0
  output_tokens: int = 0
  thought_tokens: int = 0
  cost_list_usd: float = 0.0  # every input token at full list price
  cost_billed_usd: float = 0.0  # cached input tokens at cached price
  error: str = ""
  extra: dict = field(default_factory=dict)

  def as_dict(self) -> dict:
    return asdict(self)


_TOKEN_CACHE = {"tok": "", "at": 0.0}


def _token() -> str:
  """Returns an OAuth token, refreshed every 30 minutes.

  Order: ACCESS_TOKEN env var, then the ACCESS_TOKEN_CMD shell command, then
  `gcloud auth print-access-token`.
  """
  if os.environ.get("ACCESS_TOKEN"):
    return os.environ["ACCESS_TOKEN"].strip()
  if _TOKEN_CACHE["tok"] and time.time() - _TOKEN_CACHE["at"] < 1800:
    return _TOKEN_CACHE["tok"]
  cmd = os.environ.get("ACCESS_TOKEN_CMD")
  if cmd:
    tok = subprocess.check_output(cmd, shell=True, text=True).strip()
  else:
    tok = subprocess.check_output(
        ["gcloud", "auth", "print-access-token"], text=True
    ).strip()
  _TOKEN_CACHE.update(tok=tok, at=time.time())
  return tok


def _endpoint(model: str) -> tuple[str, dict]:
  # Vertex wins when a project is set, so a stray GEMINI_API_KEY in the
  # environment does not silently switch backends.
  key = os.environ.get("GEMINI_API_KEY")
  if key and not os.environ.get("GOOGLE_CLOUD_PROJECT"):
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent"
    )
    return url, {"x-goog-api-key": key}
  project = os.environ["GOOGLE_CLOUD_PROJECT"]
  loc = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
  host = (
      "aiplatform.googleapis.com"
      if loc == "global"
      else f"{loc}-aiplatform.googleapis.com"
  )
  url = (
      f"https://{host}/v1/projects/{project}/locations/{loc}/publishers/"
      f"google/models/{model}:generateContent"
  )
  return url, {
      "Authorization": f"Bearer {_token()}",
      "x-goog-user-project": project,
  }


def cost(model: str, usage: dict) -> tuple[float, float]:
  p = PRICES[model]
  prompt = usage.get("promptTokenCount", 0)
  cached = usage.get("cachedContentTokenCount", 0)
  out = usage.get("candidatesTokenCount", 0) + usage.get(
      "thoughtsTokenCount", 0
  )
  list_cost = (prompt * p["in"] + out * p["out"]) / 1e6
  billed = (
      (prompt - cached) * p["in"] + cached * p["cached"] + out * p["out"]
  ) / 1e6
  return list_cost, billed


def generate(
    model: str,
    parts: list[dict],
    *,
    thinking: str = "HIGH",
    system: str | None = None,
    json_mode: bool = False,
    media_resolution: str | None = None,
    max_output_tokens: int = 32768,
    timeout: int = 1200,
    retries: int = 3,
) -> CallResult:
  """Calls generateContent once (with retries on 429/5xx) and times it."""
  gen = {
      "maxOutputTokens": max_output_tokens,
      "thinkingConfig": {"thinkingLevel": thinking},
  }
  if json_mode:
    gen["responseMimeType"] = "application/json"
  if media_resolution:
    gen["mediaResolution"] = media_resolution
  body = {"contents": [{"role": "user", "parts": parts}], "generationConfig": gen}
  if system:
    body["systemInstruction"] = {"parts": [{"text": system}]}
  data = json.dumps(body).encode()

  last_err = ""
  for attempt in range(retries + 1):
    url, auth = _endpoint(model)
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", **auth},
    )
    t0 = time.monotonic()
    try:
      with urllib.request.urlopen(req, timeout=timeout) as r:
        resp = json.load(r)
    except urllib.error.HTTPError as e:
      last_err = f"HTTP {e.code}: {e.read()[:300]!r}"
      if e.code in (429, 500, 502, 503, 504) and attempt < retries:
        time.sleep(10 * (attempt + 1))
        continue
      return CallResult(model, thinking, "", 0.0, error=last_err)
    except Exception as e:  # pylint: disable=broad-except
      last_err = repr(e)
      if attempt < retries:
        time.sleep(10 * (attempt + 1))
        continue
      return CallResult(model, thinking, "", 0.0, error=last_err)
    secs = time.monotonic() - t0
    usage = resp.get("usageMetadata", {})
    cand = (resp.get("candidates") or [{}])[0]
    text = "".join(
        p.get("text", "")
        for p in cand.get("content", {}).get("parts", [])
        if not p.get("thought")
    )
    lc, bc = cost(model, usage)
    return CallResult(
        model=model,
        thinking=thinking,
        text=text,
        seconds=round(secs, 2),
        prompt_tokens=usage.get("promptTokenCount", 0),
        cached_tokens=usage.get("cachedContentTokenCount", 0),
        output_tokens=usage.get("candidatesTokenCount", 0),
        thought_tokens=usage.get("thoughtsTokenCount", 0),
        cost_list_usd=round(lc, 6),
        cost_billed_usd=round(bc, 6),
        extra={"finish": cand.get("finishReason", "")},
    )
  return CallResult(model, thinking, "", 0.0, error=last_err)


def parse_json(text: str) -> dict:
  """Parses a JSON object, tolerating ```json fences."""
  t = text.strip()
  if t.startswith("```"):
    t = t.split("\n", 1)[1].rsplit("```", 1)[0]
  start, end = t.find("{"), t.rfind("}")
  return json.loads(t[start : end + 1])


def append_jsonl(path: str, row: dict) -> None:
  os.makedirs(os.path.dirname(path), exist_ok=True)
  with open(path, "a", encoding="utf-8") as fh:
    fh.write(json.dumps(row) + "\n")


CONFIGS = [
    ("gemini-4-neon", "HIGH"),
    ("gemini-4-hydrogen", "HIGH"),
    ("gemini-4-hydrogen", "LOW"),
    ("gemini-3.8-flash", "HIGH"),
]
