"""TMCAL + HCRR + reopen log. Memory locally; Firestore SoR when TMC_FIRESTORE=enabled."""

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
                    quoted_firms_confidence=(quotes.firms_confidence if quotes else None) or det.confidence,
                    quoted_firms_frp=(quotes.firms_frp if quotes and quotes.firms_frp is not None else det.frp),
                    quoted_firms_satellite=(quotes.firms_satellite if quotes else None) or det.satellite,
                    quoted_shn_span={
                        "county": seg.county,
                        "route": str(seg.route),
                        "bPM": seg.bpm,
                        "ePM": seg.epm,
                    },
                    quoted_z_delta=elev.z_delta if elev else None,
                )
                self.postmiles[(seg.route_label, round(seg.bpm, 3))] = row
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
            payload.setdefault("reopen_log_id", f"reopen-{uuid.uuid4().hex[:10]}")
            self.reopen_log.append(payload)


class FirestoreStore(MemoryStore):
    """Write-through SoR. Hydrates on cold start so /reopen survives new instances."""

    COL_POSTMILES = "tmcal_postmiles"
    COL_HCRR = "tmcal_hcrr"
    COL_REOPEN = "tmcal_reopen_log"
    COL_META = "tmcal_meta"

    def __init__(self) -> None:
        super().__init__()
        from google.cloud import firestore

        project = os.environ.get("FIRESTORE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        self._db = firestore.Client(project=project)
        self._hydrate()

    def _hydrate(self) -> None:
        try:
            for doc in self._db.collection(self.COL_POSTMILES).stream():
                data = doc.to_dict() or {}
                row = _row_from_dict(data)
                if row is None:
                    continue
                self.postmiles[(row.route, round(row.bpm, 3))] = row
                self.postmiles[(row.route, round(row.pm, 3))] = row
            for doc in self._db.collection(self.COL_HCRR).stream():
                data = doc.to_dict() or {}
                hid = data.get("id") or doc.id
                self.hcrr[hid] = data
            for doc in (
                self._db.collection(self.COL_REOPEN).order_by("seq").limit(200).stream()
            ):
                data = doc.to_dict() or {}
                data.pop("seq", None)
                self.reopen_log.append(data)
            meta = self._db.collection(self.COL_META).document("jobs").get()
            if meta.exists:
                m = meta.to_dict() or {}
                self.last_bq_job_id = m.get("last_bq_job_id")
                self.last_ee_job_id = m.get("last_ee_job_id")
        except Exception:
            # Fail open to empty memory; wake can still write.
            pass

    def reset(self) -> None:
        super().reset()
        try:
            for col in (self.COL_POSTMILES, self.COL_HCRR, self.COL_REOPEN):
                for doc in self._db.collection(col).limit(500).stream():
                    doc.reference.delete()
            self._db.collection(self.COL_META).document("jobs").delete()
        except Exception:
            pass

    def apply_match(self, result: JoinResult) -> WriteResult:
        wr = super().apply_match(result)
        if not wr.write_happened:
            return wr
        try:
            batch = self._db.batch()
            for p in wr.postmiles:
                key = f"{p['route']}_{p['bPM']}"
                ref = self._db.collection(self.COL_POSTMILES).document(key.replace(".", "_"))
                row = self.postmiles.get((p["route"], round(float(p["bPM"]), 3)))
                if row:
                    batch.set(ref, _row_to_dict(row))
            if wr.hcrr_row_id and wr.hcrr_row_id in self.hcrr:
                batch.set(
                    self._db.collection(self.COL_HCRR).document(wr.hcrr_row_id),
                    self.hcrr[wr.hcrr_row_id],
                )
            batch.set(
                self._db.collection(self.COL_META).document("jobs"),
                {
                    "last_bq_job_id": self.last_bq_job_id,
                    "last_ee_job_id": self.last_ee_job_id,
                },
                merge=True,
            )
            batch.commit()
        except Exception:
            pass
        return wr

    def log_reopen(self, payload: dict) -> None:
        super().log_reopen(payload)
        try:
            seq = len(self.reopen_log)
            self._db.collection(self.COL_REOPEN).document(f"reopen-{seq:05d}").set(
                {**payload, "seq": seq}
            )
        except Exception:
            pass


def _row_to_dict(row: PostmileRow) -> dict:
    d = asdict(row)
    d["status"] = row.status.value
    return d


def _row_from_dict(data: dict) -> PostmileRow | None:
    try:
        status = PostmileStatus(data.get("status") or "OPEN")
        return PostmileRow(
            route=str(data["route"]),
            pm=float(data["pm"]),
            bpm=float(data["bpm"]),
            epm=float(data["epm"]),
            county=str(data.get("county") or ""),
            status=status,
            firms_ids=list(data.get("firms_ids") or []),
            z_delta=data.get("z_delta"),
            quoted_span=data.get("quoted_span"),
            quoted_firms_acq_time=data.get("quoted_firms_acq_time"),
            quoted_firms_confidence=data.get("quoted_firms_confidence"),
            quoted_firms_frp=data.get("quoted_firms_frp"),
            quoted_firms_satellite=data.get("quoted_firms_satellite"),
            quoted_shn_span=data.get("quoted_shn_span"),
            quoted_z_delta=data.get("quoted_z_delta"),
        )
    except Exception:
        return None


_STORE: MemoryStore | None = None
_STORE_LOCK = Lock()


def use_firestore() -> bool:
    if os.environ.get("TMC_STORE", "").lower() == "memory":
        return False
    return os.environ.get("TMC_FIRESTORE") == "enabled" and firestore_configured()


def get_store() -> MemoryStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            if use_firestore():
                try:
                    _STORE = FirestoreStore()
                except Exception:
                    _STORE = MemoryStore()
            else:
                _STORE = MemoryStore()
        return _STORE


def reset_store() -> MemoryStore:
    global _STORE
    with _STORE_LOCK:
        # Tests always want a fresh memory store.
        if use_firestore() and _STORE is not None:
            _STORE.reset()
            return _STORE
        _STORE = MemoryStore()
        return _STORE


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
