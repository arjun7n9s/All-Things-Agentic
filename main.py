"""Cloud Functions HTTP entry. Host is Functions, not Cloud Run."""

from tmc_gate.api import handle


def tmc_gate(request):
    return handle(request)
