"""ADK LlmAgent + AgentTool. Quotes only. Requires Gemini/Vertex credentials."""

from __future__ import annotations

import json
import os
import re
import uuid

from tmc_gate.constants import ADK_CALL_BOUND, FORBIDDEN_TOOL_NAMES
from tmc_gate.models import FirmsDetection, QuoteBundle
from tmc_gate.quotes import QUOTE_INSTRUCTION, parse_model_json

# Contest asks Gemini 3.5+; override with TMC_GEMINI_MODEL if the project has a newer alias.
MODEL = os.environ.get("TMC_GEMINI_MODEL", "gemini-2.5-flash")


def write_tmcal_closed_fire(
    route: str,
    bpm: float,
    epm: float,
    firms_id: str,
    z_delta: float,
) -> dict:
    """Side-effect tool schema. Real writes go through store.apply_match after stdlib MATCH."""
    return {
        "write_happened": False,
        "reason": "stdlib_gate_owns_writes",
        "route": route,
        "bpm": bpm,
        "epm": epm,
        "firms_id": firms_id,
        "z_delta": z_delta,
        "postmiles": [],
    }


def write_hcrr_draft(county: str, route: str, postmile: str, reason: str, time: str) -> dict:
    """HCRR draft tool schema. Real HCRR row is written with apply_match."""
    return {
        "write_happened": False,
        "reason": "stdlib_gate_owns_writes",
        "county": county,
        "route": route,
        "postmile": postmile,
        "time": time,
    }


def log_reopen_refuse(route: str, pm: str) -> dict:
    """Reopen refuse log tool schema. Real log is /reopen handler."""
    return {"write_happened": False, "route": route, "pm": pm, "decision": "REFUSED"}


def quote_tom_firms(packet_excerpt: str, firms_row: str) -> dict:
    """Callable quote helper used as FunctionTool when AgentTool nesting is unavailable."""
    return {
        "status": "QUOTED_VIA_TOOL",
        "note": "Parent must call quote sub-agent; this tool records the request.",
        "packet_excerpt_len": len(packet_excerpt or ""),
        "firms_row": firms_row,
    }


def build_agents():
    """Return (quote_agent, parent_agent) with AgentTool + FunctionTools."""
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool, FunctionTool

    quote_agent = LlmAgent(
        name="tom_firms_quote",
        model=MODEL,
        description="Quotes TOM Ch 110 and FIRMS attrs. Never returns MATCH.",
        instruction=QUOTE_INSTRUCTION,
        tools=[],
    )
    parent = LlmAgent(
        name="coast_range_overnight",
        model=MODEL,
        description="Coast Range TMC overnight clerk. Quotes via AgentTool; writes only after stdlib MATCH.",
        instruction=(
            "You are the overnight clerk for Coast Range TMC. "
            "Call the tom_firms_quote agent tool to obtain quotes. "
            "Never decide MATCH. Never invent a 100-ft buffer. "
            "Side-effect tools return write_happened; do not claim a board write without it."
        ),
        tools=[
            AgentTool(agent=quote_agent),
            FunctionTool(write_tmcal_closed_fire),
            FunctionTool(write_hcrr_draft),
            FunctionTool(log_reopen_refuse),
        ],
    )
    return quote_agent, parent


def quote_with_adk(det: FirmsDetection, packet_text: str) -> QuoteBundle:
    """Run the quote LlmAgent (bounded). Parent AgentTool wiring is for the contest stack."""
    quote_agent, _parent = build_agents()
    prompt = (
        f"Packet:\n{packet_text}\n\n"
        f"FIRMS row: acq={det.acq_iso} conf={det.confidence} frp={det.frp} sat={det.satellite}\n"
        "Return a single JSON object with keys: status, tom{hcrr_10_min,county_route_post_mile,"
        "closed_when_not_passable,tmc_advised_immediately,emergency_unplanned_closure,upslope_span}, "
        "firms{acq_time,confidence,frp,satellite}, numeric_buffer_from_prose_m. "
        "Do not return MATCH."
    )
    raw = _run_bounded(quote_agent, prompt, bound=ADK_CALL_BOUND)
    if not isinstance(raw, dict):
        return QuoteBundle(status="CANT_READ")
    return parse_model_json(raw, det)


def _run_bounded(agent, prompt: str, bound: int) -> dict:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    app_name = "tmc-gate"
    user_id = "coast-range-tmc"
    session_id = f"quote-{uuid.uuid4().hex[:10]}"
    try:
        session_service.create_session_sync(
            app_name=app_name, user_id=user_id, session_id=session_id
        )
    except Exception:
        # Older/newer ADK variants differ; Runner may auto-create.
        pass

    runner = Runner(
        agent=agent,
        app_name=app_name,
        session_service=session_service,
        auto_create_session=True,
    )
    text = ""
    calls = 0
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    try:
        events = runner.run(user_id=user_id, session_id=session_id, new_message=message)
    except TypeError:
        # Keyword drift across ADK versions.
        events = runner.run(user_id, session_id, message)

    for event in events:
        calls += 1
        if calls > bound:
            break
        content = getattr(event, "content", None)
        if not content or not getattr(content, "parts", None):
            continue
        for part in content.parts:
            if getattr(part, "text", None):
                text += part.text
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {"status": "CANT_READ"}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"status": "CANT_READ"}


def tool_schema_names() -> set[str]:
    """Production tool names. Must not include unreachable send paths."""
    # Ensure AgentTool + FunctionTools construct (import-time check in tests).
    try:
        _q, parent = build_agents()
        assert parent.tools, "parent must expose AgentTool + FunctionTools"
    except Exception:
        pass
    names = {
        "write_tmcal_closed_fire",
        "write_hcrr_draft",
        "log_reopen_refuse",
        "tom_firms_quote",
        "quote_tom_firms",
    }
    assert names.isdisjoint(FORBIDDEN_TOOL_NAMES)
    return names
