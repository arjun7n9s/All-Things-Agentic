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

1. Title — `/judges` masthead: Coast Range TMC · dark desk · HCRR 10 min
2. Clock — pane 6 wall vs sim
3. Wake / Pub/Sub — Network or JSON showing `pubsub.published` after Frozen A
4. Frozen A — Run wake → `write_happened: true`, `bq_job_id`, `ee_job_id`, `z_delta`
5. Board / Firestore — TMCAL board `CLOSED_FIRE` + HCRR line
6. **/reopen in address bar** — open `/tmc-gate/reopen/CA-1/PM12` (POST via judges button or curl) → `REFUSED` + three quotes
7. Frozen B — zero writes; `/reopen/CA-1/PM12` ALLOWED after reset or on open span
8. Live FIRMS GET — pane 3; say MATCH or honest empty
9. 404 — pane 5 → `/traveler-info` 404
10. `/conformance` — 3/3, `sor: firestore`
11. Console if time — BQ job / Pub/Sub / Armor / Firestore
12. Close — board + refused reopen still hold; strip any map

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
