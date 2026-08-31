"""Model Armor fail-closed wrapper. Outage ≠ pass. No-op until GCP enablement."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ArmorVerdict:
    allowed: bool
    reason: str
    configured: bool


def armor_configured() -> bool:
    return bool(os.environ.get("MODEL_ARMOR_TEMPLATE") or os.environ.get("MODEL_ARMOR_ENABLED") == "1")


def sanitize_or_refuse(text: str) -> ArmorVerdict:
    if not armor_configured():
        # Hour-0: not enabled. Do not silently treat as pass for the A10 claim.
        return ArmorVerdict(allowed=True, reason="armor_not_configured_local", configured=False)
    try:
        # Real call wired in scripts/hour0 after template exists.
        from tmc_gate.armor_gcp import sanitize

        return sanitize(text)
    except Exception as exc:  # fail-closed
        return ArmorVerdict(allowed=False, reason=f"armor_outage:{exc}", configured=True)
