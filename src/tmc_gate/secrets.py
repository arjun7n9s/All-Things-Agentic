"""Load Gemini API key from Secret Manager (prod) or env (local)."""

from __future__ import annotations

import os


def project_id() -> str:
    return os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT") or "all-things-agents-507211"


def load_gemini_api_key() -> str | None:
    env = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if env:
        return env
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id()}/secrets/gemini-api-key/versions/latest"
        resp = client.access_secret_version(request={"name": name})
        return resp.payload.data.decode("utf-8").strip()
    except Exception:
        return None


def ensure_gemini_env() -> bool:
    """Prefer Vertex AI on GCP (contest-legal). Fall back to API key locally."""
    # Cloud Functions / Vertex path — avoids API_KEY_SERVICE_BLOCKED on the project.
    if os.environ.get("K_SERVICE") or os.environ.get("FUNCTION_TARGET") or os.environ.get(
        "TMC_USE_VERTEXAI", ""
    ) == "1":
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id())
        os.environ.setdefault(
            "GOOGLE_CLOUD_LOCATION",
            os.environ.get("GOOGLE_CLOUD_LOCATION") or "us-central1",
        )
        return True
    key = load_gemini_api_key()
    if not key:
        # Still allow Vertex if ADC is present.
        if os.environ.get("GOOGLE_CLOUD_PROJECT"):
            os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
            return True
        return False
    os.environ.setdefault("GOOGLE_API_KEY", key)
    return True
