"""Overnight wake: Frozen A / Frozen B / Live. SHN is live-capable; FIRMS bytes are case-specific."""

from __future__ import annotations

import os
from pathlib import Path

from tmc_gate.firms import filter_d5, load_csv_path, native_pixel_polygon
from tmc_gate.join import FixtureElevationEngine, JoinConfig, ShapelyGeometryEngine, evaluate
from tmc_gate.models import Decision, ElevationSample, FirmsDetection, JoinResult, QuoteBundle
from tmc_gate.shn import load_geojson_path, unique_spans

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"


def production_mode() -> bool:
    return os.environ.get("TMC_EARTH_ENGINE") == "enabled"


def default_shn_path() -> Path:
    return FIXTURES / "shn" / "mon_ca1.geojson"


def default_firms_csv() -> Path:
    return FIXTURES / "firms" / "J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv"


def frozen_a_filter(det: FirmsDetection) -> bool:
    # 30 Aug 09:26 UTC NOAA-20 Plaskett / Timber overpass (probed).
    if det.acq_date != "2026-08-30":
        return False
    if det.acq_time.zfill(4) != "0926":
        return False
    lat, lon = det.latitude, det.longitude
    plaskett = 35.85 <= lat <= 36.05 and -121.55 <= lon <= -121.35
    timber = 36.15 <= lat <= 36.35 and -121.90 <= lon <= -121.65
    return plaskett or timber


def frozen_b_filter(det: FirmsDetection) -> bool:
    """Ventana-interior / east-of-range: same overpass, east of the coastal SHN."""
    if det.acq_date != "2026-08-30":
        return False
    lat, lon = det.latitude, det.longitude
    return 35.90 <= lat <= 36.30 and -121.40 <= lon <= -121.20


def load_shn():
    path = default_shn_path()
    extra = FIXTURES / "shn" / "d5_clip.geojson"
    segs = load_geojson_path(path) if path.exists() else []
    if extra.exists():
        segs.extend(load_geojson_path(extra))
    return unique_spans(segs)


def _engines(upslope: bool = True) -> JoinConfig:
    """Production: BQ ST_Intersects + EE NASADEM. Local/tests: Shapely + fixture DEM."""
    if production_mode():
        from tmc_gate.bq_engine import BqGeometryEngine
        from tmc_gate.ee_engine import EeNasademEngine

        return JoinConfig(geometry_engine=BqGeometryEngine(), elevation_engine=EeNasademEngine())
    elev = FixtureElevationEngine(520.0, 85.0) if upslope else FixtureElevationEngine(12.0, 90.0)
    return JoinConfig(geometry_engine=ShapelyGeometryEngine(), elevation_engine=elev)


def run_case(case: str, live_bytes: bytes | None = None, unattended: bool = False) -> dict:
    """Overnight wake via ADK tools (prod) or the same tool pipeline (local/tests)."""
    from tmc_gate.adk_agent import run_overnight_with_adk
    from tmc_gate.agent_tools import run_tool_pipeline
    from tmc_gate.quotes import gemini_configured

    if case not in {"frozen_a", "frozen_b", "live"}:
        raise ValueError(case)

    # Prefer ADK orchestration when Gemini is available; tools are always the side effects.
    if gemini_configured() and os.environ.get("TMC_ADK_ORCHESTRATE", "1") != "0":
        try:
            return run_overnight_with_adk(case, live_bytes=live_bytes, unattended=unattended)
        except Exception as exc:
            err = str(exc)
            # Smart shed: 429 on 3.7 → retry overnight once on 3.5, same FunctionTools.
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                from tmc_gate.model_router import resolve

                shed = resolve("overnight_retry")
                prev = os.environ.get("TMC_GEMINI_MODEL_OVERNIGHT")
                os.environ["TMC_GEMINI_MODEL_OVERNIGHT"] = shed
                try:
                    out = run_overnight_with_adk(case, live_bytes=live_bytes, unattended=unattended)
                    out["orchestrator"] = "adk_agent_after_429_shed"
                    out["gemini_shed"] = shed
                    out["adk_error_primary"] = err[:300]
                    return out
                except Exception as exc2:
                    err = f"{err} | shed_failed:{exc2}"
                finally:
                    if prev is None:
                        os.environ.pop("TMC_GEMINI_MODEL_OVERNIGHT", None)
                    else:
                        os.environ["TMC_GEMINI_MODEL_OVERNIGHT"] = prev
            out = run_tool_pipeline(case, live_bytes=live_bytes, unattended=unattended)
            out["orchestrator"] = "tool_pipeline_after_adk_error"
            out["adk_error"] = err[:500]
            return out
    return run_tool_pipeline(case, live_bytes=live_bytes, unattended=unattended)


def _evaluate_prod_hit(
    det: FirmsDetection,
    segs,
    quotes: QuoteBundle,
    hit_map: dict,
    config: JoinConfig,
    bq_job_id: str | None,
) -> JoinResult:
    """MATCH only from BQ batch hits + EE NASADEM. No Shapely fallback."""
    from tmc_gate.constants import VIIRS_OK_CONF

    if quotes.status != "QUOTED" or not quotes.tom_quotes_ok() or not quotes.upslope_quoted():
        return JoinResult(Decision.CANT_READ, "tom_or_upslope_cant_read", detection=det, quotes=quotes)
    conf = (quotes.firms_confidence or det.confidence or "").strip().lower()
    if conf not in VIIRS_OK_CONF:
        return JoinResult(Decision.CANT_READ, "low_confidence", detection=det, quotes=quotes)

    spans = hit_map.get(det.firms_id) or []
    if not spans:
        return JoinResult(
            Decision.NON_MATCH,
            "no_st_intersects",
            detection=det,
            quotes=quotes,
            bq_job_id=bq_job_id,
        )

    matched = []
    elev_used: ElevationSample | None = None
    for county, route, bpm, epm in spans:
        seg = next(
            (
                s
                for s in segs
                if s.county == county
                and s.route == route
                and abs(s.bpm - bpm) < 1e-6
                and abs(s.epm - epm) < 1e-6
            ),
            None,
        )
        if seg is None:
            continue
        try:
            elev = config.elevation_engine.sample(det, seg)  # type: ignore[union-attr]
        except Exception:
            return JoinResult(
                Decision.CANT_READ,
                "ee_nasadem_missing",
                detection=det,
                quotes=quotes,
                bq_job_id=bq_job_id,
            )
        if elev.z_delta > config.epsilon_m:
            matched.append(seg)
            elev_used = elev

    if not matched:
        return JoinResult(
            Decision.NON_MATCH,
            "downslope_or_at_grade",
            detection=det,
            quotes=quotes,
            bq_job_id=bq_job_id,
            ee_job_id=getattr(config.elevation_engine, "_job_id", None),
        )
    return JoinResult(
        Decision.MATCH,
        "intersect_and_upslope",
        matched_segments=matched,
        detection=det,
        elevation=elev_used,
        quotes=quotes,
        bq_job_id=bq_job_id,
        ee_job_id=elev_used.ee_job_id if elev_used else None,
    )
