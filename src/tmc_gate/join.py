"""Stdlib conjunction. MATCH is never the LLM. Delete BQ or EE → cannot MATCH."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from shapely.geometry import Polygon
from shapely.ops import nearest_points

from tmc_gate.constants import D5_COUNTIES, VIIRS_OK_CONF
from tmc_gate.firms import native_pixel_polygon
from tmc_gate.models import (
    Decision,
    ElevationSample,
    FirmsDetection,
    JoinResult,
    QuoteBundle,
    ShnSegment,
)


class GeometryEngine(Protocol):
    def intersects(self, footprint: Polygon, segment: ShnSegment) -> bool: ...

    @property
    def job_id(self) -> str | None: ...


class ElevationEngine(Protocol):
    def sample(self, det: FirmsDetection, segment: ShnSegment) -> ElevationSample: ...


class ShapelyGeometryEngine:
    """Local stand-in for BigQuery ST_Intersects. Production wires BqGeometryEngine."""

    def __init__(self, job_id: str = "local-shapely-st-intersects"):
        self._job_id = job_id

    @property
    def job_id(self) -> str | None:
        return self._job_id

    def intersects(self, footprint: Polygon, segment: ShnSegment) -> bool:
        return bool(footprint.intersects(segment.geometry))


class FixtureElevationEngine:
    """Test/local DEM. Production wires Earth Engine NASADEM. Do not skip."""

    def __init__(self, z_hotspot: float, z_shn: float, job_id: str = "local-nasadem-fixture"):
        self.z_hotspot = z_hotspot
        self.z_shn = z_shn
        self._job_id = job_id

    def sample(self, det: FirmsDetection, segment: ShnSegment) -> ElevationSample:
        return ElevationSample(z_hotspot=self.z_hotspot, z_shn=self.z_shn, ee_job_id=self._job_id)


class DownslopeElevationEngine(FixtureElevationEngine):
    def __init__(self):
        super().__init__(z_hotspot=12.0, z_shn=80.0, job_id="local-nasadem-downslope")


@dataclass
class JoinConfig:
    geometry_engine: GeometryEngine | None
    elevation_engine: ElevationEngine | None
    epsilon_m: float = 0.0  # strict > when the upslope *rule* is quoted; not a 100-ft buffer


def _confidence_ok(det: FirmsDetection, quotes: QuoteBundle) -> bool:
    conf = (quotes.firms_confidence or det.confidence or "").strip().lower()
    if conf in VIIRS_OK_CONF:
        return True
    try:
        return float(conf) >= 80.0  # MODIS numeric, only if quoted as number
    except ValueError:
        return False


def evaluate(
    det: FirmsDetection,
    segments: list[ShnSegment],
    quotes: QuoteBundle,
    config: JoinConfig,
) -> JoinResult:
    """Three-object conjunction. Either engine missing → cannot MATCH."""

    if quotes.illicit_match_token is not None:
        # Presence is recorded; it is never evaluated as MATCH.
        pass

    if quotes.status != "QUOTED" or not quotes.tom_quotes_ok():
        return JoinResult(Decision.CANT_READ, "tom_quote_missing", detection=det, quotes=quotes)

    if not quotes.upslope_quoted():
        return JoinResult(Decision.CANT_READ, "upslope_span_cant_read", detection=det, quotes=quotes)

    if not _confidence_ok(det, quotes):
        return JoinResult(Decision.CANT_READ, "low_confidence", detection=det, quotes=quotes)

    if config.geometry_engine is None:
        return JoinResult(
            Decision.CANT_READ,
            "bq_st_intersects_missing",
            detection=det,
            quotes=quotes,
        )

    if config.elevation_engine is None:
        return JoinResult(
            Decision.CANT_READ,
            "ee_nasadem_missing",
            detection=det,
            quotes=quotes,
        )

    buffer_m = quotes.numeric_buffer_from_prose_m
    if buffer_m is not None and abs(buffer_m - 30.48) < 0.01:
        return JoinResult(Decision.CANT_READ, "invented_100ft_buffer_ignored", detection=det, quotes=quotes)

    footprint = native_pixel_polygon(det)
    hits: list[ShnSegment] = []
    for seg in segments:
        if not seg.d5 or seg.county not in D5_COUNTIES:
            continue
        if config.geometry_engine.intersects(footprint, seg):
            hits.append(seg)

    if not hits:
        return JoinResult(
            Decision.NON_MATCH,
            "no_st_intersects",
            detection=det,
            quotes=quotes,
            bq_job_id=config.geometry_engine.job_id,
        )

    matched: list[ShnSegment] = []
    elev_used: ElevationSample | None = None
    for seg in hits:
        elev = config.elevation_engine.sample(det, seg)
        if elev.z_delta > config.epsilon_m:
            matched.append(seg)
            elev_used = elev
        # downslope / at-grade / ocean-side: skip this segment

    if not matched:
        return JoinResult(
            Decision.NON_MATCH,
            "downslope_or_at_grade",
            detection=det,
            quotes=quotes,
            bq_job_id=config.geometry_engine.job_id,
            ee_job_id=getattr(config.elevation_engine, "_job_id", None),
        )

    return JoinResult(
        Decision.MATCH,
        "intersect_and_upslope",
        matched_segments=matched,
        detection=det,
        elevation=elev_used,
        quotes=quotes,
        bq_job_id=config.geometry_engine.job_id,
        ee_job_id=elev_used.ee_job_id if elev_used else None,
    )


def county_only_closer(det: FirmsDetection, county: str = "MON") -> bool:
    """ANTI-PATTERN. Illegally over-broad. Tests must fail this as a closer."""
    # Deliberately wrong: treats any detection as a Monterey closure.
    return county.upper() in {"MON", "MONTEREY"} and det.latitude > 0


def nearest_shn_point_wkt(det: FirmsDetection, segment: ShnSegment) -> str:
    fp = native_pixel_polygon(det)
    p, _ = nearest_points(fp.centroid, segment.geometry)
    return p.wkt
