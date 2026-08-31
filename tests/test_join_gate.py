"""Stdlib-gate tests. Do not claim 320. Names are load-bearing."""

from __future__ import annotations

from pathlib import Path

import pytest

from tmc_gate.constants import FIRMS_CSV, FIRMS_KML, UNREACHABLE_PATHS
from tmc_gate.firms import invented_100ft_buffer_m, is_ee_firms_url, live_gun_urls, load_csv_path, native_pixel_polygon
from tmc_gate.join import (
    FixtureElevationEngine,
    JoinConfig,
    ShapelyGeometryEngine,
    county_only_closer,
    evaluate,
)
from tmc_gate.models import Decision, FirmsDetection, QuoteBundle
from tmc_gate.quotes import packet_quotes_for, parse_model_json
from tmc_gate.shn import load_geojson_path, unique_spans
from tmc_gate.store import reset_store
from tmc_gate.wake import frozen_a_filter, run_case

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "fixtures" / "firms" / "J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv"
SHN = ROOT / "fixtures" / "shn" / "mon_ca1.geojson"


def _plaskett() -> FirmsDetection:
    dets = [d for d in load_csv_path(CSV) if frozen_a_filter(d)]
    assert dets, "frozen A FIRMS bytes missing"
    segs = _segs()
    cfg = _upslope()
    for d in dets:
        r = evaluate(d, segs, packet_quotes_for(d), cfg)
        if r.decision is Decision.MATCH:
            return d
    raise AssertionError("no Frozen A detection ST_Intersects SHN with native pixel")


def _segs():
    return unique_spans(load_geojson_path(SHN))


def _quotes(det, **over):
    q = packet_quotes_for(det)
    return QuoteBundle(**{**q.__dict__, **over})


def _upslope():
    return JoinConfig(
        geometry_engine=ShapelyGeometryEngine(),
        elevation_engine=FixtureElevationEngine(520.0, 80.0),
    )


def test_match_intersect_and_upslope():
    det = _plaskett()
    r = evaluate(det, _segs(), packet_quotes_for(det), _upslope())
    assert r.decision is Decision.MATCH
    assert r.matched_segments
    wr = reset_store().apply_match(r)
    assert wr.write_happened is True
    assert wr.postmiles
    assert wr.hcrr_row_id


def test_nonmatch_ventana_inland():
    inland = FirmsDetection(
        latitude=36.18,
        longitude=-121.28,
        acq_date="2026-08-30",
        acq_time="0926",
        satellite="N20",
        confidence="nominal",
        frp=9.0,
        scan_km=0.375,
        track_km=0.375,
    )
    r = evaluate(inland, _segs(), packet_quotes_for(inland), _upslope())
    assert r.decision is not Decision.MATCH
    wr = reset_store().apply_match(r)
    assert wr.write_happened is False
    assert wr.postmiles == []


def test_cant_read_low_confidence():
    det = _plaskett()
    q = _quotes(det, firms_confidence="low")
    r = evaluate(det, _segs(), q, _upslope())
    assert r.decision is Decision.CANT_READ
    assert r.reason == "low_confidence"


def test_county_only_must_fail():
    inland = FirmsDetection(
        latitude=36.18,
        longitude=-121.28,
        acq_date="2026-08-30",
        acq_time="0926",
        satellite="N20",
        confidence="nominal",
        frp=9.0,
        scan_km=0.375,
        track_km=0.375,
    )
    assert county_only_closer(inland, "MONTEREY") is True
    r = evaluate(inland, _segs(), packet_quotes_for(inland), _upslope())
    assert r.decision is not Decision.MATCH


def test_delete_ee_cannot_match():
    det = _plaskett()
    cfg = JoinConfig(geometry_engine=ShapelyGeometryEngine(), elevation_engine=None)
    r = evaluate(det, _segs(), packet_quotes_for(det), cfg)
    assert r.decision is not Decision.MATCH
    assert r.reason == "ee_nasadem_missing"


def test_delete_bq_cannot_match():
    det = _plaskett()
    cfg = JoinConfig(
        geometry_engine=None,
        elevation_engine=FixtureElevationEngine(520.0, 80.0),
    )
    r = evaluate(det, _segs(), packet_quotes_for(det), cfg)
    assert r.decision is not Decision.MATCH
    assert r.reason == "bq_st_intersects_missing"


def test_no_invented_100ft_buffer():
    assert invented_100ft_buffer_m() is None
    det = _plaskett()
    poly = native_pixel_polygon(det)
    # Native VIIRS pixel ~0.375 km, not 100 ft (30.48 m).
    minx, miny, maxx, maxy = poly.bounds
    # Rough width in metres at this latitude.
    width_m = (maxx - minx) * 111_320 * 0.81  # cos(36°)
    assert width_m > 200  # much larger than 100 ft
    src = (ROOT / "src" / "tmc_gate" / "firms.py").read_text(encoding="utf-8")
    assert "buffer(100" not in src
    assert "30.48" in src  # only as the forbidden value we refuse


def test_llm_never_returns_match():
    det = _plaskett()
    parsed = parse_model_json(
        {
            "status": "QUOTED",
            "MATCH": True,
            "decision": "MATCH",
            "tom": {
                "county_route_post_mile": "county, route, and post mile",
                "upslope_span": "steep slope above the highway",
                "hcrr_10_min": "10 minutes",
            },
            "firms": {"confidence": "nominal", "acq_time": det.acq_iso, "frp": det.frp, "satellite": "N20"},
        },
        det,
    )
    assert parsed.illicit_match_token is not None
    r = evaluate(det, _segs(), parsed, _upslope())
    # Gate still conjuncts; MATCH is not taken from the token.
    assert r.decision in {Decision.MATCH, Decision.NON_MATCH, Decision.CANT_READ}
    # A quotes-missing payload with MATCH token still cannot MATCH.
    empty = parse_model_json({"status": "CANT_READ", "decision": "MATCH"}, det)
    r2 = evaluate(det, _segs(), empty, _upslope())
    assert r2.decision is Decision.CANT_READ


def test_live_gun_is_csv_kml_not_ee_firms():
    urls = live_gun_urls()
    assert "firms.modaps.eosdis.nasa.gov" in urls["csv"]
    assert urls["csv"].endswith(".csv")
    assert urls["kml"].endswith(".kml")
    assert not is_ee_firms_url(urls["csv"])
    assert is_ee_firms_url("https://earthengine.googleapis.com/v1/projects/x/imageCollection/FIRMS")
    assert "FIRMS" not in FIRMS_CSV["noaa20"]
    from tmc_gate.constants import EE_FIRMS_COLLECTION

    assert EE_FIRMS_COLLECTION == "FIRMS"
    assert FIRMS_KML["noaa20"].startswith("https://firms.modaps.eosdis.nasa.gov/")


def test_hcrr_row_write_happened():
    reset_store()
    out = run_case("frozen_a")
    assert out["write_happened"] is True
    assert out["hcrr_row_id"]
    from tmc_gate.store import get_store

    assert get_store().hcrr[out["hcrr_row_id"]]["write_happened"] is True
