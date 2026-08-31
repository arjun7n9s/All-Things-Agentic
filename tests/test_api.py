from __future__ import annotations

import pytest

from tmc_gate.adk_agent import tool_schema_names
from tmc_gate.api import create_app
from tmc_gate.constants import FORBIDDEN_TOOL_NAMES, UNREACHABLE_PATHS
from tmc_gate.store import get_store, reset_store
from tmc_gate.wake import run_case


@pytest.fixture
def client():
    reset_store()
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


def test_reopen_refused_includes_quotes(client):
    run_case("frozen_a")
    # Honest closed span this fixture: MON CA-1 bPM 0–25.806 (contains PM12). Not county-wide.
    rv = client.post("/reopen/CA-1/PM12")
    assert rv.status_code == 200
    body = rv.get_json()
    assert body["decision"] == "REFUSED"
    assert body["quoted_firms_acq_time"]
    assert body["quoted_shn_span"]
    assert body["quoted_z_delta"] is not None
    assert body["write_happened"] is False
    assert body["status"] == "CLOSED_FIRE"


def test_reopen_allowed_on_open_frozen_b(client):
    run_case("frozen_b")
    rv = client.post("/reopen/CA-1/PM12")
    body = rv.get_json()
    assert body["decision"] == "ALLOWED"
    assert body["status"] == "OPEN"
    assert body["reason"] == "no_closed_fire_conjunct"


def test_unreachable_404(client):
    for path in UNREACHABLE_PATHS:
        rv = client.get(path)
        assert rv.status_code == 404, path
    assert tool_schema_names().isdisjoint(FORBIDDEN_TOOL_NAMES)


def test_conformance_3_of_3(client):
    run_case("frozen_a")
    client.post("/reopen/CA-1/PM12")
    rv = client.get("/conformance")
    body = rv.get_json()
    assert body["checks"]["postmile_status_closed_fire"] is True
    assert body["checks"]["quoted_spans_present"] is True
    assert body["checks"]["hcrr_row_present"] is True
    assert body["score"] == "3/3"


def test_no_cloud_run():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    main = (root / "main.py").read_text(encoding="utf-8")
    assert "functions_framework" in (root / "pyproject.toml").read_text(encoding="utf-8") or "tmc_gate" in main
    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "not Cloud Run" in readme or "Not Cloud Run" in readme or "not `.run.app`" in readme
    # Deployable entry is Functions, not a Cloud Run service yaml.
    assert not (root / "service.yaml").exists()
    assert "run.app" not in main


def test_reopen_pm47_not_county_webhook(client):
    """Frozen A closed Gorda (0–25.8). PM47 on the same route stays OPEN."""
    run_case("frozen_a")
    rv = client.post("/reopen/CA-1/PM47")
    assert rv.get_json()["decision"] == "ALLOWED"


def test_health_pending_enable(client):
    rv = client.get("/health")
    body = rv.get_json()
    assert body["ok"] is True
    assert body["host"] == "cloud-functions"
    assert body["not_cloud_run"] is True
    assert body["live_gun"] == "firms_csv_kml"
    assert body["ee_firms_not_live_gun"] is True
    assert body["fixture_tmc"] == "Coast Range TMC"
