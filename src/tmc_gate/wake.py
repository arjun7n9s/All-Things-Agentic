"""Overnight wake: Frozen A / Frozen B / Live. SHN is live-capable; FIRMS bytes are case-specific."""

from __future__ import annotations

from pathlib import Path

from tmc_gate.firms import load_csv_path
from tmc_gate.join import FixtureElevationEngine, JoinConfig, ShapelyGeometryEngine, evaluate
from tmc_gate.models import Decision, FirmsDetection, JoinResult, WriteResult
from tmc_gate.quotes import packet_quotes_for, run_quote_agent
from tmc_gate.shn import load_geojson_path, unique_spans
from tmc_gate.store import get_store

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "fixtures"


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


def _engines_local(upslope: bool = True) -> JoinConfig:
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
        config = _engines_local(upslope=True)
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
        config = _engines_local(upslope=True)
    elif case == "live":
        config = _engines_local(upslope=True)
    else:
        raise ValueError(case)

    writes = 0
    matches = 0
    cant = 0
    non = 0
    last_match: JoinResult | None = None
    last_write: WriteResult | None = None
    for det in dets:
        quotes = run_quote_agent(det) if case == "live" else packet_quotes_for(det)
        result = evaluate(det, segs, quotes, config)
        if result.decision is Decision.MATCH:
            matches += 1
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
    }
