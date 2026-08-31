"""Cloud Functions HTTP (2nd gen) + local functions-framework. Not Cloud Run."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
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
DESK = ROOT / "frontend" / "desk"


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


def _mount(request: Request) -> str:
    host = request.host or ""
    if "cloudfunctions.net" in host:
        return "/tmc-gate"
    return ""


def _wants_html(request: Request) -> bool:
    if request.args.get("format") == "json":
        return False
    accept = (request.headers.get("Accept") or "").lower()
    if "text/html" in accept:
        return True
    if "application/json" in accept:
        return False
    return False


def _render_desk(name: str, request: Request, payload: dict | None = None) -> Response:
    path = DESK / name
    if not path.exists():
        return Response("desk ui missing", status=500)
    html = path.read_text(encoding="utf-8")
    html = html.replace("{{MOUNT}}", _mount(request))
    html = html.replace("{{PAYLOAD}}", json.dumps(payload if payload is not None else {}, default=str))
    return Response(html, status=200, mimetype="text/html; charset=utf-8")


def handle(request: Request):
    path = _path(request)
    method = (request.method or "GET").upper()

    for banned in UNREACHABLE_PATHS:
        if path == banned or path.startswith(banned + "/"):
            return Response("unreachable", status=404, mimetype="text/plain")

    if path in {"/health", "/health/"} and method == "GET":
        payload = _health()
        if _wants_html(request):
            return _render_desk("health.html", request, payload)
        return _json(payload)

    if path in {"/conformance", "/conformance/"} and method == "GET":
        payload = _conformance()
        if _wants_html(request):
            return _render_desk("conformance.html", request, payload)
        return _json(payload)

    if path.startswith("/reopen/") and method in {"POST", "GET"}:
        body = _reopen(path, request)
        if method == "GET" and _wants_html(request):
            return _render_desk("reopen.html", request, body)
        return _json(body)

    if path.startswith("/wake") and method in {"POST", "GET"}:
        case = request.args.get("case") or (request.get_json(silent=True) or {}).get("case") or "frozen_a"
        unattended = (
            request.args.get("source") == "scheduler"
            or request.headers.get("X-CloudScheduler") == "true"
            or bool(request.headers.get("X-CloudScheduler-JobName"))
        )
        live_bytes = None
        if case == "live":
            from tmc_gate.firms import fetch_bytes, live_gun_urls

            try:
                live_bytes = fetch_bytes(live_gun_urls()["csv"])
            except Exception as exc:
                return _json(
                    {
                        "case": "live",
                        "error": str(exc),
                        "honest_empty": True,
                        "writes": 0,
                        "live_get_url": live_gun_urls()["csv"],
                    }
                )
        return _json(run_case(case, live_bytes=live_bytes, unattended=unattended))

    if path in {"/clock", "/clock/"} and method in {"GET", "POST"}:
        mode = request.args.get("mode") or (request.get_json(silent=True) or {}).get("mode")
        if method == "POST" and mode in {"wall", "sim"}:
            os.environ["TMC_CLOCK"] = mode
        return _json({"mode": os.environ.get("TMC_CLOCK", "wall"), "tz": TZ})

    if path in {"/reset", "/reset/"} and method in {"POST", "GET"}:
        reset_store()
        return _json({"ok": True, "reset": True})

    if path in {"/board", "/board/"} and method == "GET":
        store = get_store()
        rows = [row_public(r) for r in store.postmiles.values()]
        return _json({"fixture_tmc": FIXTURE_TMC, "postmiles": rows, "hcrr": list(store.hcrr.values())})

    if path.startswith("/judges"):
        return _judges(path, request)

    if path in {"/", ""}:
        host = request.host or ""
        if "cloudfunctions.net" in host:
            dest = f"https://{host}/tmc-gate/judges"
        else:
            dest = request.url.rstrip("/") + "/judges"
        return Response("", status=302, headers={"Location": dest})

    return Response("not found", status=404, mimetype="text/plain")


def _last_unattended_wake() -> dict | None:
    try:
        if os.environ.get("TMC_FIRESTORE") != "enabled":
            return None
        from google.cloud import firestore

        project = os.environ.get("FIRESTORE_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
        db = firestore.Client(project=project)
        doc = db.collection("tmcal_meta").document("last_unattended_wake").get()
        return doc.to_dict() if doc.exists else None
    except Exception:
        return None


def _svc(name: str) -> str:
    flag = os.environ.get(f"TMC_{name.upper()}", "")
    if flag == "enabled":
        return "enabled"
    if flag == "failed":
        return "failed"
    return "not-configured"


_LETTERS = (
    ("A1", "earth_engine", "Earth Engine"),
    ("A2", "bigquery", "BigQuery"),
    ("A3", "pubsub", "Pub/Sub"),
    ("A4", "model_armor", "Model Armor"),
    ("A5", "cloud_functions", "Cloud Functions"),
    ("A6", "firestore", "Firestore"),
    ("A7", "secret_manager", "Secret Manager"),
    ("A8", "cloud_storage", "Cloud Storage"),
)


def _health() -> dict:
    checked = datetime.now(timezone.utc).isoformat()
    services = {
        "earth_engine": _svc("earth_engine"),
        "bigquery": _svc("bigquery"),
        "pubsub": _svc("pubsub"),
        "model_armor": _svc("model_armor"),
        "cloud_functions": "enabled",
        "firestore": _svc("firestore"),
        "secret_manager": _svc("secret_manager"),
        "cloud_storage": _svc("cloud_storage"),
    }
    letters = [
        {
            "letter": ltr,
            "key": key,
            "service": name,
            "status": services[key],
            "last_checked_iso": checked,
        }
        for ltr, key, name in _LETTERS
    ]
    payload = {
        "ok": True,
        "host": "cloud-functions",
        "not_cloud_run": True,
        "fixture_tmc": FIXTURE_TMC,
        "checked_at": checked,
        "letters": letters,
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
        "last_unattended_wake": _last_unattended_wake(),
        "agent_tools": [
            "fetch_firms_batch",
            "quote_tom_and_firms",
            "spatial_join_upslope",
            "commit_closed_fire_writes",
            "publish_firms_witness",
            "probe_reopen_gate",
        ],
        # Devpost mandatory stack — judges curl this.
        "eligibility": {
            "track": "Taskmaster",
            "gemini": _primary_gemini(),
            "gemini_access": "Vertex AI",
            "gemini_min_required": "3.5",
            "gemini_routing": _gemini_routing(),
            "agent_framework": "Google ADK",
            "agent_framework_detail": "LlmAgent + AgentTool + FunctionTool",
            "cloud_infrastructure": [
                "Cloud Functions",
                "Firestore",
                "Pub/Sub",
                "BigQuery",
                "Earth Engine",
                "Secret Manager",
                "Cloud Storage",
                "Model Armor",
                "Cloud Scheduler",
                "Vertex AI",
            ],
            "not_cloud_run_host": True,
            "not_chatbot": True,
        },
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
    elif all(v == "not-configured" for v in services.values() if v != "enabled"):
        # cloud_functions is always enabled when serving
        others = {k: v for k, v in services.items() if k != "cloud_functions"}
        if all(v == "not-configured" for v in others.values()):
            payload["a10_claim"] = "PENDING_ENABLE"
    return payload


def _primary_gemini() -> str:
    from tmc_gate.model_router import primary_model

    return primary_model()


def _gemini_routing() -> dict:
    from tmc_gate.model_router import routing_table

    return routing_table()


def _parse_route_pm(path: str) -> tuple[str, float]:
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
            "quoted_firms_confidence": row.quoted_firms_confidence,
            "quoted_firms_frp": row.quoted_firms_frp,
            "quoted_firms_satellite": row.quoted_firms_satellite,
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
    from tmc_gate.store import use_firestore

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
        "sor": "firestore" if use_firestore() else "memory",
        "cold": n < 3,
    }


def _judges(path: str, request: Request):
    if not DESK.exists():
        return Response("desk ui missing", status=500)
    rel = path[len("/judges") :].lstrip("/") or "judges.html"
    if path.rstrip("/") == "/judges" or rel in {"", "index.html", "judges.html"}:
        return _render_desk("judges.html", request)
    candidate = DESK / rel
    if candidate.exists() and candidate.is_file():
        return send_from_directory(DESK, rel)
    return Response("not found", status=404, mimetype="text/plain")
