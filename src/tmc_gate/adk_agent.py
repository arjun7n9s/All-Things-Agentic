"""ADK LlmAgent + AgentTool. Quotes only. Requires Gemini/Vertex credentials."""

from __future__ import annotations

from tmc_gate.constants import ADK_CALL_BOUND, FORBIDDEN_TOOL_NAMES
from tmc_gate.models import FirmsDetection, QuoteBundle
from tmc_gate.quotes import QUOTE_INSTRUCTION, parse_model_json

MODEL = "gemini-3.5-flash"


def quote_with_adk(det: FirmsDetection, packet_text: str) -> QuoteBundle:
    from google.adk.agents import LlmAgent

    # Tools that mutate TMCAL live on the parent; this sub-agent quotes only.
    quote_agent = LlmAgent(
        name="tom_firms_quote",
        model=MODEL,
        instruction=QUOTE_INSTRUCTION,
        tools=[],
    )
    prompt = (
        f"Packet:\n{packet_text}\n\n"
        f"FIRMS row: acq={det.acq_iso} conf={det.confidence} frp={det.frp} sat={det.satellite}\n"
        "Return JSON quotes. Do not return MATCH."
    )
    # Bounded run. google-adk Runner API varies by version; keep a hard cap.
    raw = _run_bounded(quote_agent, prompt, bound=ADK_CALL_BOUND)
    if not isinstance(raw, dict):
        return QuoteBundle(status="CANT_READ")
    return parse_model_json(raw, det)


def _run_bounded(agent, prompt: str, bound: int) -> dict:
    import json
    import re

    from google.adk.runners import Runner
    from google.genai import types

    runner = Runner(agent=agent)
    text = ""
    calls = 0
    for event in runner.run(user_id="coast-range-tmc", session_id="quote", new_message=types.Content(role="user", parts=[types.Part(text=prompt)])):
        calls += 1
        if calls > bound:
            break
        if getattr(event, "content", None) and event.content.parts:
            for part in event.content.parts:
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
    names = {"write_tmcal_closed_fire", "write_hcrr_draft", "log_reopen_refuse", "quote_tom_firms"}
    assert names.isdisjoint(FORBIDDEN_TOOL_NAMES)
    return names
