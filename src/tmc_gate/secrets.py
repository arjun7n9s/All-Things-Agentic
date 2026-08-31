"""Load Gemini / AIMLAPI keys from env, .env, or Secret Manager. Never log secret values."""

from __future__ import annotations

import os
from pathlib import Path


def project_id() -> str:
    return os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT") or "all-things-agents-507211"


def load_dotenv_file(path: Path | None = None) -> None:
    """Best-effort local .env loader (no python-dotenv dependency)."""
    root = Path(__file__).resolve().parents[2]
    env_path = path or (root / ".env")
    if not env_path.is_file():
        return
    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            key = key.strip()
            val = val.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = val
    except Exception:
        pass


def _secret_latest(secret_id: str) -> str | None:
    try:
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id()}/secrets/{secret_id}/versions/latest"
        resp = client.access_secret_version(request={"name": name})
        return resp.payload.data.decode("utf-8").strip()
    except Exception:
        return None


def load_gemini_api_key() -> str | None:
    env = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if env:
        return env
    return _secret_latest("gemini-api-key")


def load_aimlapi_key() -> str | None:
    """AIMLAPI_KEY — OpenAI-compatible Gemini fallback."""
    load_dotenv_file()
    env = (
        os.environ.get("AIMLAPI_KEY")
        or os.environ.get("AIML_API_KEY")
        or os.environ.get("AIMLAPI_API_KEY")
    )
    if env:
        return env.strip()
    return _secret_latest("aimlapi-key")


def ensure_gemini_env() -> bool:
    """Prefer Vertex AI on GCP. AIMLAPI_KEY alone also counts as configured (fallback path)."""
    load_dotenv_file()
    # Cloud Functions / Vertex path — avoids API_KEY_SERVICE_BLOCKED on the project.
    if os.environ.get("K_SERVICE") or os.environ.get("FUNCTION_TARGET") or os.environ.get(
        "TMC_USE_VERTEXAI", ""
    ) == "1":
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project_id())
        # Gemini 3.5 Flash on Vertex is served from location=global (not us-central1).
        os.environ.setdefault(
            "GOOGLE_CLOUD_LOCATION",
            os.environ.get("GOOGLE_CLOUD_LOCATION") or "global",
        )
        # Ensure AIMLAPI is visible for quote fallback even when Vertex is primary.
        load_aimlapi_key()
        return True
    key = load_gemini_api_key()
    if key:
        os.environ.setdefault("GOOGLE_API_KEY", key)
        return True
    if load_aimlapi_key():
        return True
    # Still allow Vertex if ADC is present.
    if os.environ.get("GOOGLE_CLOUD_PROJECT"):
        os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "true")
        return True
    return False
