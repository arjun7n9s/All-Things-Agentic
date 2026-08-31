# Demo film shot list — Coast Range TMC / tmc-gate

~4 minutes. Unedited screen recording. Host URL only:

`https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate`

Do **not** show `.run.app`. Do not lead with a map.

## Honest product URLs for this fire

Frozen A (Plaskett/Timber 30 Aug 2026 09:26 UTC) closes **CA-1 bPM 0–25.806**.

| Action | URL |
|---|---|
| Judges | `/tmc-gate/judges` |
| **REFUSED reopen** | `POST /tmc-gate/reopen/CA-1/PM12` |
| Not a county webhook | `POST /tmc-gate/reopen/CA-1/PM47` → **ALLOWED** after Frozen A |

Say on camera: “PM47 is still a valid product URL; it refuses only when *that* span is CLOSED_FIRE.”

## Record in this order

Show the app working in the first 10–15 seconds. No long intro. No typing live.

1. Title — `/judges` masthead: Coast Range TMC · dark desk · HCRR 10 min
2. `/health` eligibility strip — **gemini-3.5-flash · Vertex AI · Google ADK · Firestore/Pub/Sub/Functions** (mandatory stack proof)
3. Clock — wall vs sim
4. Frozen A — recorded MATCH · CLOSED_FIRE · write log · `→ POST /reopen/CA-1/PM12`
5. **/reopen in address bar** — `/tmc-gate/reopen/CA-1/PM12` → `REFUSED` + three quotes
6. Frozen B — NON-MATCH zero writes; PM47 ALLOWED (not a county webhook)
7. Live FIRMS GET strip — MATCH or honest empty
8. 404 — unreachable paths
9. `/conformance` — 3/3, `sor: firestore`
10. **GCP proof (required)** — Cloud Console: Cloud Functions service + Vertex AI / Firestore / Pub/Sub (rules demand visible GCP backend)
11. Close — board + refused reopen still hold; strip any map

## Curl cheat-sheet (second monitor OK)

```powershell
$B="https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate"
curl.exe -sS "$B/health"
curl.exe -sS "$B/wake?case=frozen_a"
curl.exe -sS -X POST "$B/reopen/CA-1/PM12" -H "Content-Type: application/json" -d "{}"
curl.exe -sS -X POST "$B/reopen/CA-1/PM47" -H "Content-Type: application/json" -d "{}"
curl.exe -sS "$B/wake?case=frozen_b"
curl.exe -sS "$B/wake?case=live"
curl.exe -sS "$B/conformance"
curl.exe -sS -o NUL -w "%{http_code}" "$B/traveler-info"
```
