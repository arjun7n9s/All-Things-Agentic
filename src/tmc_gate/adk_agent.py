"""ADK LlmAgent + AgentTool. Overnight clerk calls real FunctionTools that mutate TMCAL."""

from __future__ import annotations

import json
import os
import re
import uuid

from tmc_gate.constants import ADK_CALL_BOUND, FORBIDDEN_TOOL_NAMES
from tmc_gate.models import FirmsDetection, QuoteBundle
from tmc_gate.quotes import QUOTE_INSTRUCTION, parse_model_json

MODEL = os.environ.get("TMC_GEMINI_MODEL", "gemini-2.5-flash")

OVERNIGHT_INSTRUCTION = """You are the overnight clerk for Coast Range TMC (fixture TMC).

You MUST call tools to move data. You NEVER invent MATCH. MATCH is only returned by
spatial_join_upslope (BigQuery + Earth Engine stdlib).

Required tool order for an overnight wake:
1) fetch_firms_batch(case)
2) quote_tom_and_firms()
3) spatial_join_upslope()
4) commit_closed_fire_writes()  — only writes rows the join already MATCHed
5) publish_firms_witness()
6) probe_reopen_gate(route, pm) on a closed postmile if writes happened

If spatial_join_upslope reports matches=0, still call commit (it will no-op) and publish.
Never call publish_traveler_info, email, CAD, or Cloud Run tools — they do not exist.
Side-effect tools return write_happened; do not claim a board write without it.
After tools finish, reply with a short JSON summary:
{"case":"...","write_happened":true|false,"matches":N,"reopen_url":"..."}
"""


def build_agents():
    """Return (quote_agent, parent_agent) with AgentTool + real FunctionTools."""
    from google.adk.agents import LlmAgent
    from google.adk.tools import AgentTool, FunctionTool

    from tmc_gate.agent_tools import (
        commit_closed_fire_writes,
        fetch_firms_batch,
        probe_reopen_gate,
        publish_firms_witness,
        quote_tom_and_firms,
        spatial_join_upslope,
    )

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
        description="Coast Range TMC overnight clerk. Fetches FIRMS, quotes, joins via stdlib tools, writes TMCAL.",
        instruction=OVERNIGHT_INSTRUCTION,
        tools=[
            AgentTool(agent=quote_agent),
            FunctionTool(fetch_firms_batch),
            FunctionTool(quote_tom_and_firms),
            FunctionTool(spatial_join_upslope),
            FunctionTool(commit_closed_fire_writes),
            FunctionTool(publish_firms_witness),
            FunctionTool(probe_reopen_gate),
        ],
    )
    return quote_agent, parent


def quote_with_adk(det: FirmsDetection, packet_text: str) -> QuoteBundle:
    """Run the quote LlmAgent (bounded)."""
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


def run_overnight_with_adk(case: str, live_bytes: bytes | None = None, unattended: bool = False) -> dict:
    """ADK parent agent drives the tool chain. If it skips a required tool, pipeline recovers."""
    from tmc_gate.agent_tools import (
        begin_session,
        commit_closed_fire_writes,
        fetch_firms_batch,
        probe_reopen_gate,
        publish_firms_witness,
        quote_tom_and_firms,
        record_unattended_wake,
        run_tool_pipeline,
        session,
        session_payload,
        spatial_join_upslope,
    )
    from tmc_gate.quotes import gemini_configured

    # Local/tests: deterministic tool pipeline (same tools, no LLM orchestration).
    if not gemini_configured() or os.environ.get("TMC_ADK_ORCHESTRATE") == "0":
        return run_tool_pipeline(case, live_bytes=live_bytes, unattended=unattended)

    begin_session(case, live_bytes=live_bytes, unattended=unattended)
    _quote_agent, parent = build_agents()
    prompt = (
        f"Overnight wake. case={case}. "
        "Call fetch_firms_batch, quote_tom_and_firms, spatial_join_upslope, "
        "commit_closed_fire_writes, publish_firms_witness, then probe_reopen_gate if writes happened. "
        "Do not invent MATCH."
    )
    text, called = _run_agent_collect(parent, prompt, bound=ADK_CALL_BOUND)

    required = {
        "fetch_firms_batch",
        "quote_tom_and_firms",
        "spatial_join_upslope",
        "commit_closed_fire_writes",
        "publish_firms_witness",
    }
    called_set = set(called)
    recovered = []
    # If the model talked instead of tooling, execute missing steps ourselves (same tools).
    if "fetch_firms_batch" not in called_set:
        fetch_firms_batch(case)
        recovered.append("fetch_firms_batch")
    if "quote_tom_and_firms" not in called_set:
        quote_tom_and_firms()
        recovered.append("quote_tom_and_firms")
    if "spatial_join_upslope" not in called_set:
        spatial_join_upslope()
        recovered.append("spatial_join_upslope")
    if "commit_closed_fire_writes" not in called_set:
        commit_closed_fire_writes()
        recovered.append("commit_closed_fire_writes")
    if "publish_firms_witness" not in called_set:
        publish_firms_witness()
        recovered.append("publish_firms_witness")

    s = session()
    if s.writes and not any(t.get("tool") == "probe_reopen_gate" for t in s.tool_trace):
        if s.reopen_url and s.reopen_url.count("/") >= 2:
            parts = s.reopen_url.strip("/").split("/")
            probe_reopen_gate(parts[1], parts[2])
        else:
            probe_reopen_gate("CA-1", "12")
        recovered.append("probe_reopen_gate")

    if unattended:
        record_unattended_wake()

    payload = session_payload(
        orchestrator="adk_agent" if not recovered else "adk_agent_recovered",
        agent_text=text,
        adk_tool_calls=called,
    )
    if recovered:
        payload["recovered_tools"] = recovered
    return payload


def _run_agent_collect(agent, prompt: str, bound: int) -> tuple[str, list[str]]:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types

    session_service = InMemorySessionService()
    app_name = "tmc-gate"
    user_id = "coast-range-tmc"
    session_id = f"overnight-{uuid.uuid4().hex[:10]}"
    try:
        session_service.create_session_sync(app_name=app_name, user_id=user_id, session_id=session_id)
    except Exception:
        pass

    runner = Runner(agent=agent, app_name=app_name, session_service=session_service, auto_create_session=True)
    text = ""
    called: list[str] = []
    calls = 0
    message = types.Content(role="user", parts=[types.Part(text=prompt)])
    try:
        events = runner.run(user_id=user_id, session_id=session_id, new_message=message)
    except TypeError:
        events = runner.run(user_id, session_id, message)

    for event in events:
        calls += 1
        if calls > bound * 3:
            break
        # Function-call parts
        content = getattr(event, "content", None)
        if content and getattr(content, "parts", None):
            for part in content.parts:
                fc = getattr(part, "function_call", None)
                if fc is not None and getattr(fc, "name", None):
                    called.append(fc.name)
                if getattr(part, "text", None):
                    text += part.text
        # Some ADK versions expose get_function_calls
        get_fc = getattr(event, "get_function_calls", None)
        if callable(get_fc):
            for fc in get_fc() or []:
                name = getattr(fc, "name", None)
                if name:
                    called.append(name)
    return text, called


def _run_bounded(agent, prompt: str, bound: int) -> dict:
    text, _called = _run_agent_collect(agent, prompt, bound=bound)
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return {"status": "CANT_READ"}
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return {"status": "CANT_READ"}


def tool_schema_names() -> set[str]:
    names = {
        "fetch_firms_batch",
        "quote_tom_and_firms",
        "spatial_join_upslope",
        "commit_closed_fire_writes",
        "publish_firms_witness",
        "probe_reopen_gate",
        "tom_firms_quote",
        "write_tmcal_closed_fire",
        "write_hcrr_draft",
        "log_reopen_refuse",
    }
    assert names.isdisjoint(FORBIDDEN_TOOL_NAMES)
    try:
        _q, parent = build_agents()
        assert parent.tools
    except Exception:
        pass
    return names
