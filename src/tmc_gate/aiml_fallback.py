"""AIMLAPI OpenAI-compatible Gemini fallback when Vertex / Google API key fail."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

from tmc_gate.models import FirmsDetection, QuoteBundle
from tmc_gate.quotes import QUOTE_INSTRUCTION, parse_model_json

AIMLAPI_BASE = os.environ.get("AIMLAPI_BASE", "https://api.aimlapi.com/v1").rstrip("/")
# Prefer Gemini 3.7, stay ≥3.5 (hackathon floor). Override with TMC_AIMLAPI_MODEL.
DEFAULT_MODELS = (
    os.environ.get("TMC_AIMLAPI_MODEL"),
    "google/gemini-3.7-flash",
    "gemini-3.7-flash",
    "google/gemini-3.5-flash",
    "gemini-3.5-flash",
)


def aimlapi_configured() -> bool:
    from tmc_gate.secrets import load_aimlapi_key

    return bool(load_aimlapi_key())


def quote_with_aimlapi(det: FirmsDetection, packet_text: str) -> QuoteBundle:
    """Chat-completions quote path. Raises on total transport failure."""
    from tmc_gate.secrets import load_aimlapi_key

    key = load_aimlapi_key()
    if not key:
        raise RuntimeError("AIMLAPI_KEY missing")

    prompt = (
        f"{QUOTE_INSTRUCTION}\n\n"
        f"Packet:\n{packet_text}\n\n"
        f"FIRMS row: acq={det.acq_iso} conf={det.confidence} frp={det.frp} sat={det.satellite}\n"
        "Return ONLY a JSON object with keys: status, tom{hcrr_10_min,county_route_post_mile,"
        "closed_when_not_passable,tmc_advised_immediately,emergency_unplanned_closure,upslope_span}, "
        "firms{acq_time,confidence,frp,satellite}, numeric_buffer_from_prose_m. "
        "status must be QUOTED or CANT_READ. Do not return MATCH."
    )
    last_err: Exception | None = None
    for model in DEFAULT_MODELS:
        if not model:
            continue
        try:
            text = _chat_completion(key, model, prompt)
            raw = _extract_json(text)
            if not isinstance(raw, dict):
                continue
            bundle = parse_model_json(raw, det)
            if bundle.status == "QUOTED" or bundle.tom_quotes_ok():
                return bundle
            # Keep trying other models if parse was empty/cant-read noise.
            if bundle.status == "CANT_READ":
                last_err = RuntimeError(f"aimlapi_cant_read:{model}")
                continue
            return bundle
        except Exception as exc:
            last_err = exc
            continue
    if last_err:
        raise last_err
    raise RuntimeError("aimlapi_no_model_worked")


def _chat_completion(api_key: str, model: str, user_prompt: str) -> str:
    body = json.dumps(
        {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 2048,
            "messages": [
                {
                    "role": "system",
                    "content": "You quote verbatim policy and FIRMS fields as JSON. Never decide MATCH.",
                },
                {"role": "user", "content": user_prompt},
            ],
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        f"{AIMLAPI_BASE}/chat/completions",
        data=body,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "tmc-gate/0.1",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:400]
        raise RuntimeError(f"aimlapi_http_{exc.code}:{detail}") from exc
    choices = payload.get("choices") or []
    if not choices:
        raise RuntimeError("aimlapi_empty_choices")
    msg = choices[0].get("message") or {}
    content = msg.get("content")
    if isinstance(content, list):
        # Multimodal-style content parts
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("text"):
                parts.append(str(part["text"]))
            elif isinstance(part, str):
                parts.append(part)
        content = "\n".join(parts)
    if not content:
        raise RuntimeError("aimlapi_empty_content")
    return str(content)


def _extract_json(text: str) -> dict | None:
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
