"""Model Armor sanitize via REST. Fail-closed on outage."""

from __future__ import annotations

import json
import os
import urllib.request

from tmc_gate.armor import ArmorVerdict
from tmc_gate.secrets import project_id


def sanitize(text: str) -> ArmorVerdict:
    template = os.environ.get("MODEL_ARMOR_TEMPLATE")
    if not template:
        return ArmorVerdict(allowed=False, reason="armor_template_missing", configured=True)
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    url = (
        f"https://modelarmor.{location}.rep.googleapis.com/v1/{template}:sanitizeUserPrompt"
    )
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
        # If Model Armor returns a block / match, refuse.
        result = payload.get("sanitizationResult") or payload
        filter_results = result.get("filterResults") or {}
        # Conservative: if any filter has MATCH / BLOCKED style state, refuse.
        blocked = False
        reason = "ok"
        for name, fr in filter_results.items() if isinstance(filter_results, dict) else []:
            state = str(fr.get("raiFilterResult", fr.get("piAndJailbreakFilterResult", fr)))
            if "MATCH" in state.upper() or "BLOCK" in state.upper():
                blocked = True
                reason = f"armor_{name}"
                break
        if blocked:
            return ArmorVerdict(allowed=False, reason=reason, configured=True)
        return ArmorVerdict(allowed=True, reason="armor_pass", configured=True)
    except Exception as exc:
        return ArmorVerdict(allowed=False, reason=f"armor_outage:{exc}", configured=True)
