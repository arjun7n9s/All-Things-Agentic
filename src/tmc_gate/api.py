"""Cloud Functions HTTP (2nd gen) + local functions-framework. Not Cloud Run."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from flask import Flask, Request, Response, send_from_directory

from tmc_gate.constants import (
    D5_CLOSE,
    D5_OPEN,
    FILM_PM,
    FILM_ROUTE,
    FIXTURE_TMC,
    TZ,
    UNREACHABLE_PATHS,
)
from tmc_gate.models import PostmileStatus
from tmc_gate.store import get_store, reset_store, row_public
from tmc_gate.wake import run_case

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend" / "judges"


def create_app() -> Flask:
    app = Flask(__name__)

    @app.route("/", defaults={"path": ""}, methods=["GET", "POST"])
    @app.route("/<path:path>", methods=["GET", "POST"])
    def catch(path: str):  # noqa: ARG001
        from flask import request

        return handle(request)

    return app

_PM_RE = re.compile(r"PM?([0-9]+(?:\.[0-9]+)?)$", re.I)


def _json(payload: dict, status: int = 200) -> Response:
    return Response(json.dumps(payload, default=str), status=status, mimetype="application/json")


def _path(request: Request) -> str:
    p = request.path or "/"
    if p.startswith("/tmc-gate"):
        p = p[len("/tmc-gate") :] or "/"
    return p


def handle(request: Request):
    path = _path(request)
    method = (request.method or "GET").upper()

    for banned in UNREACHABLE_PATHS:
        if path == banned or path.startswith(banned + "/"):
            return Response("unreachable", status=404, mimetype="text/plain")

    if path in {"/health", "/health/"} and method == "GET":
        return _json(_health())

    if path in {"/conformance", "/conformance/"} and method == "GET":
        return _json(_conformance())

    if path.startswith("/reopen/") and method in {"POST", "GET"}:
        return _json(_reopen(path, request))

    if path.startswith("/wake") and method in {"POST", "GET"}:
        case = request.args.get("case") or (request.get_json(silent=True) or {}).get("case") or "frozen_a"
        live_bytes = None
        if case == "live":
            from tmc_gate.firms import fetch_bytes, live_gun_urls

            try:
                live_bytes = fetch_bytes(live_gun_urls()["csv"])
            except Exception as exc:
                return _json({"case": "live", "error": str(exc), "honest_empty": True, "writes": 0})
        return _json(run_case(case, live_bytes=live_bytes))

    if path in {"/reset"} and method == "POST":
        reset_store()
        return _json({"ok": True, "reset": True})

    if path in {"/board", "/board/"} and method == "GET":
        store = get_store()
        rows = [row_public(r) for r in store.postmiles.values()]
        return _json({"fixture_tmc": FIXTURE_TMC, "postmiles": rows, "hcrr": list(store.hcrr.values())})

    if path.startswith("/judges"):
        return _judges(path)

    if path in {"/", ""}:
        # cloudfunctions.net serves the function under /tmc-gate; *.run.app is root.
        host = request.host or ""
        if "cloudfunctions.net" in host:
            dest = f"https://{host}/tmc-gate/judges"
        else:
            dest = request.url.rstrip("/") + "/judges"
        return Response("", status=302, headers={"Location": dest})

    return Response("not found", status=404, mimetype="text/plain")


def _svc(name: str) -> str:
    flag = os.environ.get(f"TMC_{name.upper()}", "")
    if flag == "enabled":
        return "enabled"
    if flag == "failed":
        return "failed"
    return "not-configured"


def _health() -> dict:
    services = {
        "earth_engine": _svc("earth_engine"),
        "bigquery": _svc("bigquery"),
        "pubsub": _svc("pubsub"),
        "model_armor": _svc("model_armor"),
        "firestore": _svc("firestore"),
        "secret_manager": _svc("secret_manager"),
        "cloud_storage": _svc("cloud_storage"),
    }
    payload = {
        "ok": True,
        "host": "cloud-functions",
        "not_cloud_run": True,
        "fixture_tmc": FIXTURE_TMC,
        "services": services,
        "clock": {
            "mode": os.environ.get("TMC_CLOCK", "wall"),
            "tz": TZ,
            "d5_tmc_open": D5_OPEN,
            "d5_tmc_close": D5_CLOSE,
            "weekdays_only": True,
        },
        "live_gun": "firms_csv_kml",
        "ee_firms_not_live_gun": True,
    }
    failed = [k for k, v in services.items() if v == "failed"]
    if "earth_engine" in failed or "model_armor" in failed:
        payload["a10_claim"] = "FAILED"
        if "earth_engine" in failed:
            payload["failed_letter"] = (
                "Earth Engine FAILED — join cannot MATCH without NASADEM; do not close on intersect-only"
            )
        elif "model_armor" in failed:
            payload["failed_letter"] = "Model Armor FAILED — A8 (U10/A8/D8 = 88)"
    elif all(v == "not-configured" for v in services.values()):
        payload["a10_claim"] = "PENDING_ENABLE"
    return payload


def _parse_route_pm(path: str) -> tuple[str, float]:
    # /reopen/CA-1/PM47
    parts = [p for p in path.split("/") if p]
    if len(parts) < 3:
        return FILM_ROUTE, 47.0
    route = parts[1]
    m = _PM_RE.search(parts[2])
    pm = float(m.group(1)) if m else float(parts[2])
    return route, pm


def _reopen(path: str, request: Request) -> dict:
    route, pm = _parse_route_pm(path)
    store = get_store()
    row = store.find(route, pm)
    if row and row.status is PostmileStatus.CLOSED_FIRE:
        body = {
            "decision": "REFUSED",
            "route": row.route,
            "pm": str(int(pm) if pm == int(pm) else pm),
            "status": "CLOSED_FIRE",
            "quoted_firms_acq_time": row.quoted_firms_acq_time,
            "quoted_shn_span": row.quoted_shn_span,
            "quoted_z_delta": row.quoted_z_delta,
            "firms_ids": row.firms_ids,
            "write_happened": False,
            "reason": "upslope_footprint_still_intersects",
        }
        store.log_reopen(body)
        return body
    body = {
        "decision": "ALLOWED",
        "route": route.upper() if route.upper().startswith("CA-") else f"CA-{route}",
        "pm": str(int(pm) if pm == int(pm) else pm),
        "status": "OPEN",
        "reason": "no_closed_fire_conjunct",
        "write_happened": False,
    }
    store.log_reopen(body)
    return body


def _first_closed(store):
    for row in store.postmiles.values():
        if row.status is PostmileStatus.CLOSED_FIRE:
            return row
    return store.find(FILM_ROUTE, 47.0)


def _conformance() -> dict:
    store = get_store()
    row = _first_closed(store)
    closed = bool(row and row.status is PostmileStatus.CLOSED_FIRE)
    quotes_ok = bool(row and row.quoted_firms_acq_time and row.quoted_shn_span and row.quoted_z_delta is not None)
    refuse = any(x.get("decision") == "REFUSED" for x in store.reopen_log)
    hcrr = bool(store.hcrr)
    ee = bool(store.last_ee_job_id)
    bq = bool(store.last_bq_job_id)
    n = sum([closed, quotes_ok, refuse or hcrr])
    score = "3/3" if n >= 3 else f"{n}/3"
    return {
        "score": score,
        "checks": {
            "postmile_status_closed_fire": closed,
            "quoted_spans_present": quotes_ok,
            "reopen_refuse_log_present": refuse,
            "hcrr_row_present": hcrr,
            "ee_job_id_present": ee,
            "bq_job_id_present": bq,
        },
        "objects": {
            "route": row.route if row else FILM_ROUTE,
            "pm": str(int(row.pm) if row and row.pm == int(row.pm) else (row.pm if row else "47")),
            "status": row.status.value if row else "OPEN",
            "quoted_firms_acq_time": row.quoted_firms_acq_time if row else None,
            "quoted_shn_span": row.quoted_shn_span if row else None,
            "quoted_z_delta": row.quoted_z_delta if row else None,
        },
        "cold": n < 3,
    }


def _judges(path: str):
    rel = path[len("/judges") :].lstrip("/") or "index.html"
    if not FRONTEND.exists():
        return Response("judges ui missing", status=500)
    if rel == "index.html" or path.rstrip("/") == "/judges":
        return send_from_directory(FRONTEND, "index.html")
    candidate = FRONTEND / rel
    if candidate.exists() and candidate.is_file():
        return send_from_directory(FRONTEND, rel)
    return send_from_directory(FRONTEND, "index.html")
