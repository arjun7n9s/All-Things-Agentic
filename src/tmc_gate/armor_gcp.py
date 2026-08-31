"""Model Armor sanitize via REST. Fail-closed on outage."""

from __future__ import annotations

import json
import os
import urllib.request

from tmc_gate.armor import ArmorVerdict


def sanitize(text: str) -> ArmorVerdict:
    template = os.environ.get("MODEL_ARMOR_TEMPLATE")
    if not template:
        return ArmorVerdict(allowed=False, reason="armor_template_missing", configured=True)
    # Model Armor templates live in a regional location; Vertex Gemini 3.5 uses global.
    location = (
        os.environ.get("MODEL_ARMOR_LOCATION")
        or os.environ.get("GOOGLE_CLOUD_REGION")
        or "us-central1"
    )
    if location == "global":
        location = "us-central1"
    url = f"https://modelarmor.{location}.rep.googleapis.com/v1/{template}:sanitizeUserPrompt"
    try:
        import google.auth
        import google.auth.transport.requests

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        creds.refresh(google.auth.transport.requests.Request())
        body = json.dumps({"userPromptData": {"text": text}}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={
                "Authorization": f"Bearer {creds.token}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        result = payload.get("sanitizationResult") or payload
        # Top-level state is authoritative. Do NOT substring-match "MATCH"
        # inside "NO_MATCH_FOUND".
        state = str(result.get("filterMatchState") or "")
        if state == "MATCH_FOUND":
            return ArmorVerdict(allowed=False, reason="armor_match_found", configured=True)
        if state in {"NO_MATCH_FOUND", ""}:
            return ArmorVerdict(allowed=True, reason="armor_pass", configured=True)
        # Unknown state → fail closed
        return ArmorVerdict(allowed=False, reason=f"armor_unknown_state:{state}", configured=True)
    except Exception as exc:
        return ArmorVerdict(allowed=False, reason=f"armor_outage:{exc}", configured=True)
