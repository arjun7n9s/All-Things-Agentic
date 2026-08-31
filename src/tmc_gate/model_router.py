"""Task-scoped Gemini routing. Prefer 3.7 Flash for agentic work; never below 3.5.

Architectural rule: MATCH stays stdlib. Models only quote / orchestrate tools.
"""

from __future__ import annotations

import os
from typing import Literal

Task = Literal["overnight", "overnight_retry", "quote", "quote_retry", "lite"]

# Defaults — override with TMC_GEMINI_MODEL_<TASK> or TMC_GEMINI_MODEL.
_DEFAULTS: dict[Task, str] = {
    # Multi-step tool orchestration (parent LlmAgent). 3.7 is the agentic workhorse.
    "overnight": "gemini-3.7-flash",
    # Shed when Vertex returns 429 / RESOURCE_EXHAUSTED on 3.7.
    "overnight_retry": "gemini-3.5-flash",
    # Verbatim TOM / PIO / FIRMS quote clerk (AgentTool sub-agent).
    "quote": "gemini-3.7-flash",
    # Availability shed if primary quote model 404s / refuses.
    "quote_retry": "gemini-3.5-flash",
    # Cheap probes only (never used for MATCH).
    "lite": "gemini-3.1-flash-lite",
}

# Ordered fallbacks for quote path when Vertex rejects a model id.
QUOTE_FALLBACKS = (
    "gemini-3.7-flash",
    "gemini-3.5-flash",
)


def resolve(task: Task) -> str:
    """Return the model id for a named task.

    Precedence:
    1. TMC_GEMINI_MODEL_<TASK> (e.g. TMC_GEMINI_MODEL_QUOTE_RETRY)
    2. TMC_GEMINI_MODEL — only for overnight + quote (primary path)
    3. Built-in defaults (preserves quote_retry / lite differentiation)
    """
    specific = (os.environ.get(f"TMC_GEMINI_MODEL_{task.upper()}") or "").strip()
    if specific:
        return specific
    global_m = (os.environ.get("TMC_GEMINI_MODEL") or "").strip()
    if global_m and task in {"overnight", "quote"}:
        return global_m
    return _DEFAULTS[task]


def routing_table() -> dict:
    """Judge-facing map of task → model (+ why)."""
    return {
        "overnight": {
            "model": resolve("overnight"),
            "role": "ADK parent LlmAgent — tool orchestration",
            "why": "Gemini 3.7 Flash is the agentic workhorse for multi-step FunctionTool chains",
        },
        "overnight_retry": {
            "model": resolve("overnight_retry"),
            "role": "ADK parent shed on 429 RESOURCE_EXHAUSTED",
            "why": "Stay ≥ Gemini 3.5 floor; same FunctionTools; MATCH still stdlib",
        },
        "quote": {
            "model": resolve("quote"),
            "role": "ADK AgentTool quote clerk — TOM Ch 110 + FIRMS attrs",
            "why": "Instruction-faithful verbatim quotes; never returns MATCH",
        },
        "quote_retry": {
            "model": resolve("quote_retry"),
            "role": "Availability shed if primary quote model fails",
            "why": "Stay on Gemini 3.5+ (mandatory floor) without inventing MATCH",
        },
        "lite": {
            "model": resolve("lite"),
            "role": "Optional cheap probe (not on the MATCH path)",
            "why": "Cost shed for non-decision health/ping traffic",
        },
        "access": "Vertex AI",
        "location": os.environ.get("GOOGLE_CLOUD_LOCATION", "global"),
        "mandatory_floor": "gemini-3.5",
        "primary": resolve("overnight"),
        "stdlib_decides_match": True,
    }


def primary_model() -> str:
    return resolve("overnight")
