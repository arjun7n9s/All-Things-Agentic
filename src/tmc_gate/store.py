"""TMCAL + HCRR + reopen log. Memory store for local; Firestore adapter when GCP is on."""

from __future__ import annotations

import os
import uuid
from dataclasses import asdict
from threading import Lock

from tmc_gate.models import (
    JoinResult,
    PostmileRow,
    PostmileStatus,
    WriteResult,
)


class MemoryStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self.postmiles: dict[tuple[str, float], PostmileRow] = {}
        self.hcrr: dict[str, dict] = {}
        self.reopen_log: list[dict] = []
        self.wakes: list[dict] = []
        self.last_bq_job_id: str | None = None
        self.last_ee_job_id: str | None = None

    def reset(self) -> None:
        with self._lock:
            self.postmiles.clear()
            self.hcrr.clear()
            self.reopen_log.clear()
            self.wakes.clear()
            self.last_bq_job_id = None
            self.last_ee_job_id = None

    def seed_open(self, route: str, pm: float, bpm: float, epm: float, county: str) -> None:
        key = (route, round(pm, 3))
        with self._lock:
            self.postmiles[key] = PostmileRow(
                route=route, pm=pm, bpm=bpm, epm=epm, county=county, status=PostmileStatus.OPEN
            )

    def apply_match(self, result: JoinResult) -> WriteResult:
        if result.decision.value != "MATCH" or not result.matched_segments or not result.detection:
            return WriteResult(write_happened=False, postmiles=[])
        det = result.detection
        quotes = result.quotes
        elev = result.elevation
        written: list[dict] = []
        hcrr_id = f"hcrr-{uuid.uuid4().hex[:10]}"
        with self._lock:
            self.last_bq_job_id = result.bq_job_id
            self.last_ee_job_id = result.ee_job_id
            for seg in result.matched_segments:
                row = PostmileRow(
                    route=seg.route_label,
                    pm=(seg.bpm + seg.epm) / 2.0,
                    bpm=seg.bpm,
                    epm=seg.epm,
                    county=seg.county,
                    status=PostmileStatus.CLOSED_FIRE,
                    firms_ids=[det.firms_id],
                    z_delta=elev.z_delta if elev else None,
                    quoted_span=quotes.county_route_post_mile if quotes else None,
                    quoted_firms_acq_time=quotes.firms_acq_time if quotes else det.acq_iso,
                    quoted_shn_span={
                        "county": seg.county,
                        "route": str(seg.route),
                        "bPM": seg.bpm,
                        "ePM": seg.epm,
                    },
                    quoted_z_delta=elev.z_delta if elev else None,
                )
                self.postmiles[(seg.route_label, round(seg.bpm, 3))] = row
                # Also index by film PM if the span contains it.
                from tmc_gate.constants import FILM_PM_NUMBER

                if seg.contains_pm(FILM_PM_NUMBER):
                    self.postmiles[(seg.route_label, FILM_PM_NUMBER)] = row
                written.append(
                    {
                        "route": seg.route_label,
                        "bPM": seg.bpm,
                        "ePM": seg.epm,
                        "status": "CLOSED_FIRE",
                        "firms_ids": [det.firms_id],
                        "z_delta": elev.z_delta if elev else None,
                        "quoted_span": quotes.county_route_post_mile if quotes else None,
                    }
                )
            self.hcrr[hcrr_id] = {
                "id": hcrr_id,
                "county": result.matched_segments[0].county,
                "route": str(result.matched_segments[0].route),
                "postmile": f"{result.matched_segments[0].bpm}-{result.matched_segments[0].epm}",
                "reason": "upslope_firms_footprint",
                "time": det.acq_iso,
                "write_happened": True,
            }
        return WriteResult(write_happened=True, postmiles=written, hcrr_row_id=hcrr_id)

    def find(self, route: str, pm: float) -> PostmileRow | None:
        route_n = _norm_route(route)
        with self._lock:
            direct = self.postmiles.get((route_n, round(pm, 3)))
            if direct:
                return direct
            for (r, _), row in self.postmiles.items():
                if r == route_n and row.bpm <= pm <= row.epm:
                    return row
        return None

    def log_reopen(self, payload: dict) -> None:
        with self._lock:
            self.reopen_log.append(payload)


_STORE: MemoryStore | None = None
_STORE_LOCK = Lock()


def get_store() -> MemoryStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = MemoryStore()
        return _STORE


def reset_store() -> MemoryStore:
    s = get_store()
    s.reset()
    return s


def _norm_route(route: str) -> str:
    r = route.upper().replace(" ", "")
    if r.startswith("CA-"):
        return r
    if r.isdigit():
        return f"CA-{r}"
    return r


def firestore_configured() -> bool:
    return bool(os.environ.get("FIRESTORE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT"))


def row_public(row: PostmileRow) -> dict:
    return asdict(row) | {"status": row.status.value}
