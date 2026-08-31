"""Overnight wake: Frozen A / Frozen B / Live. SHN is live-capable; FIRMS bytes are case-specific."""

from __future__ import annotations

import os
from pathlib import Path

from tmc_gate.firms import load_csv_path, native_pixel_polygon
from tmc_gate.join import FixtureElevationEngine, JoinConfig, ShapelyGeometryEngine, evaluate
from tmc_gate.models import Decision, ElevationSample, FirmsDetection, JoinResult, QuoteBundle, WriteResult
from tmc_gate.quotes import gemini_configured, packet_quotes_for, run_quote_agent
from tmc_gate.shn import load_geojson_path, unique_spans
from tmc_gate.store import get_store

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


def run_case(case: str, live_bytes: bytes | None = None) -> dict:
    store = get_store()
    segs = load_shn()
    csv_path = default_firms_csv()
    if case == "live" and live_bytes:
        from tmc_gate.firms import parse_csv

        dets = parse_csv(live_bytes.decode("utf-8", errors="replace"))
    else:
        dets = load_csv_path(csv_path) if csv_path.exists() else []

    if case == "frozen_a":
        dets = [d for d in dets if frozen_a_filter(d)]
        config = _engines(upslope=True)
    elif case == "frozen_b":
        dets = [d for d in dets if frozen_b_filter(d)]
        if not dets:
            # Honest empty inland cluster: a recorded east-of-range point that must not MATCH.
            dets = [
                FirmsDetection(
                    latitude=36.18,
                    longitude=-121.28,
                    acq_date="2026-08-30",
                    acq_time="0926",
                    satellite="N20",
                    confidence="nominal",
                    frp=8.0,
                    scan_km=0.375,
                    track_km=0.375,
                    source="frozen-b-ventana",
                )
            ]
        config = _engines(upslope=True)
    elif case == "live":
        config = _engines(upslope=True)
    else:
        raise ValueError(case)

    hit_map: dict | None = None
    bq_job_id: str | None = None
    if production_mode():
        from tmc_gate.bq_engine import BqGeometryEngine

        if not isinstance(config.geometry_engine, BqGeometryEngine) or config.elevation_engine is None:
            return {
                "case": case,
                "error": "production_requires_bq_and_ee",
                "detections": len(dets),
                "matches": 0,
                "writes": 0,
                "write_happened": False,
            }
        fps = [(d.firms_id, native_pixel_polygon(d)) for d in dets]
        hit_map = config.geometry_engine.intersecting_spans(fps)
        bq_job_id = config.geometry_engine.job_id

    writes = 0
    matches = 0
    cant = 0
    non = 0
    last_match: JoinResult | None = None
    last_write: WriteResult | None = None
    matched_firms: list[str] = []

    # One bounded ADK quote run per wake when Gemini is configured (prod).
    # Reuse TOM spans; FIRMS attrs stay per-detection. Avoids N Gemini calls.
    adk_bundle: QuoteBundle | None = None
    adk_used = False
    if dets and gemini_configured() and (production_mode() or case == "live"):
        adk_bundle = run_quote_agent(dets[0])
        adk_used = adk_bundle.status == "QUOTED"

    for det in dets:
        if adk_used and adk_bundle is not None:
            quotes = QuoteBundle(
                status=adk_bundle.status,
                hcrr_10_min=adk_bundle.hcrr_10_min,
                county_route_post_mile=adk_bundle.county_route_post_mile,
                closed_when_not_passable=adk_bundle.closed_when_not_passable,
                tmc_advised_immediately=adk_bundle.tmc_advised_immediately,
                emergency_unplanned_closure=adk_bundle.emergency_unplanned_closure,
                upslope_span=adk_bundle.upslope_span,
                firms_acq_time=det.acq_iso,
                firms_confidence=det.confidence,
                firms_frp=det.frp,
                firms_satellite=det.satellite,
                numeric_buffer_from_prose_m=adk_bundle.numeric_buffer_from_prose_m,
            )
        elif case == "live":
            quotes = run_quote_agent(det)
        else:
            quotes = packet_quotes_for(det)

        if production_mode() and os.environ.get("MODEL_ARMOR_ENABLED") == "1":
            from tmc_gate.armor import sanitize_or_refuse

            verdict = sanitize_or_refuse(quotes.upslope_span or quotes.county_route_post_mile or "")
            if verdict.configured and not verdict.allowed:
                cant += 1
                continue

        if production_mode() and hit_map is not None:
            result = _evaluate_prod_hit(det, segs, quotes, hit_map, config, bq_job_id)
        else:
            result = evaluate(det, segs, quotes, config)

        if result.decision is Decision.MATCH:
            matches += 1
            matched_firms.append(det.firms_id)
            wr = store.apply_match(result)
            if wr.write_happened:
                writes += 1
                last_write = wr
                last_match = result
        elif result.decision is Decision.CANT_READ:
            cant += 1
        else:
            non += 1

    store.wakes.append({"case": case, "n": len(dets), "matches": matches, "writes": writes})
    reopen_url = None
    if last_write and last_write.postmiles:
        p = last_write.postmiles[0]
        reopen_url = f"/reopen/{p['route']}/PM{int(p['bPM']) if p['bPM']==int(p['bPM']) else p['bPM']}"
        # Prefer a whole-number PM inside the span for the product URL.
        for cand in (12, 0.09, 47, 56):
            if p["bPM"] <= cand <= p["ePM"]:
                label = f"PM{int(cand)}" if cand == int(cand) else f"PM{cand}"
                reopen_url = f"/reopen/{p['route']}/{label}"
                break

    pubsub_meta = {"published": False, "reason": "skipped"}
    if production_mode():
        from tmc_gate.pubsub_bus import publish_wake_batch

        pubsub_meta = publish_wake_batch(
            case=case,
            firms_ids=matched_firms or [d.firms_id for d in dets[:8]],
            detections=len(dets),
            matches=matches,
            write_happened=bool(last_write and last_write.write_happened),
            bq_job_id=last_match.bq_job_id if last_match else bq_job_id,
            ee_job_id=last_match.ee_job_id if last_match else None,
        )

    return {
        "case": case,
        "detections": len(dets),
        "matches": matches,
        "non_match": non,
        "cant_read": cant,
        "writes": writes,
        "write_happened": bool(last_write and last_write.write_happened),
        "postmiles": last_write.postmiles if last_write else [],
        "hcrr_row_id": last_write.hcrr_row_id if last_write else None,
        "honest_empty": case == "live" and matches == 0,
        "bq_job_id": last_match.bq_job_id if last_match else None,
        "ee_job_id": last_match.ee_job_id if last_match else None,
        "reopen_url": reopen_url,
        "production": production_mode(),
        "adk_quotes": adk_used,
        "pubsub": pubsub_meta,
    }


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
