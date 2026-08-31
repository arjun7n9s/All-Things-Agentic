"""Cloud Functions HTTP entry. Host is Functions, not Cloud Run."""

from __future__ import annotations

import sys
from pathlib import Path

# Cloud Functions build packs the repo root; package lives under src/.
_SRC = Path(__file__).resolve().parent / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from tmc_gate.api import handle  # noqa: E402
from tmc_gate.secrets import ensure_gemini_env, load_aimlapi_key, load_dotenv_file  # noqa: E402


def tmc_gate(request):
    load_dotenv_file()
    ensure_gemini_env()
    load_aimlapi_key()  # populate AIMLAPI_KEY from Secret Manager if needed
    return handle(request)
