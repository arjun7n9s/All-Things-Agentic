from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Decision(str, Enum):
    MATCH = "MATCH"
    NON_MATCH = "NON_MATCH"
    CANT_READ = "CANT_READ"


class PostmileStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED_FIRE = "CLOSED_FIRE"


@dataclass(frozen=True)
class QuoteBundle:
    """Gemini quotes. The LLM never returns MATCH that the gate evaluates."""

    status: str  # QUOTED | CANT_READ
    hcrr_10_min: str | None = None
    county_route_post_mile: str | None = None
    closed_when_not_passable: str | None = None
    tmc_advised_immediately: str | None = None
    emergency_unplanned_closure: str | None = None
    upslope_span: str | None = None
    firms_acq_time: str | None = None
    firms_confidence: str | None = None
    firms_frp: float | None = None
    firms_satellite: str | None = None
    numeric_buffer_from_prose_m: float | None = None
    # If the model emits this, the gate MUST ignore it.
    illicit_match_token: Any = None

    def tom_quotes_ok(self) -> bool:
        return self.status == "QUOTED" and bool(self.county_route_post_mile)

    def upslope_quoted(self) -> bool:
        if not self.upslope_span:
            return False
        span = self.upslope_span.lower()
        return "slope above" in span or "steep slope above" in span or "above the highway" in span


@dataclass
class FirmsDetection:
    latitude: float
    longitude: float
    acq_date: str
    acq_time: str  # HHMM UTC
    satellite: str
    confidence: str
    frp: float
    scan_km: float
    track_km: float
    daynight: str = ""
    source: str = "noaa20"

    @property
    def acq_iso(self) -> str:
        hh, mm = self.acq_time.zfill(4)[:2], self.acq_time.zfill(4)[2:]
        return f"{self.acq_date}T{hh}:{mm}:00Z"

    @property
    def firms_id(self) -> str:
        sat = self.satellite.replace(" ", "")
        return f"{sat}-{self.latitude:.5f}-{self.longitude:.5f}-{self.acq_date.replace('-', '')}T{self.acq_time.zfill(4)}"


@dataclass
class ShnSegment:
    county: str
    route: int
    bpm: float
    epm: float
    wkt: str
    geometry: Any  # shapely geometry; typed Any to avoid import cycle
    d5: bool = True

    @property
    def route_label(self) -> str:
        return f"CA-{self.route}"

    def contains_pm(self, pm: float) -> bool:
        lo, hi = (self.bpm, self.epm) if self.bpm <= self.epm else (self.epm, self.bpm)
        return lo <= pm <= hi


@dataclass
class ElevationSample:
    z_hotspot: float
    z_shn: float
    ee_job_id: str | None = None

    @property
    def z_delta(self) -> float:
        return self.z_hotspot - self.z_shn


@dataclass
class JoinResult:
    decision: Decision
    reason: str
    matched_segments: list[ShnSegment] = field(default_factory=list)
    detection: FirmsDetection | None = None
    elevation: ElevationSample | None = None
    quotes: QuoteBundle | None = None
    bq_job_id: str | None = None
    ee_job_id: str | None = None


@dataclass
class WriteResult:
    write_happened: bool
    postmiles: list[dict] = field(default_factory=list)
    hcrr_row_id: str | None = None


@dataclass
class PostmileRow:
    route: str
    pm: float
    bpm: float
    epm: float
    county: str
    status: PostmileStatus
    firms_ids: list[str] = field(default_factory=list)
    z_delta: float | None = None
    quoted_span: str | None = None
    quoted_firms_acq_time: str | None = None
    quoted_firms_confidence: str | None = None
    quoted_firms_frp: float | None = None
    quoted_firms_satellite: str | None = None
    quoted_shn_span: dict | None = None
    quoted_z_delta: float | None = None
