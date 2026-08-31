# Demo film shot list — maps 1:1 to spec `12-demo-video.md`

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
| Refusal certificate | `GET /tmc-gate/reopen/CA-1/PM12?format=cert` |

Say on camera: “PM47 is still a valid product URL; it refuses only when *that* span is CLOSED_FIRE.”

## Shot list (order = completed actions · matches 12-demo-video.md)

| # | Shot | On screen | Says in 10 seconds | Do not |
|---|---|---|---|---|
| 1 | Title | `/judges` masthead: Coast Range TMC · dark desk · HCRR 10 min | Fire on the slope above Highway 1. PM still OPEN. Cannot reopen at 6. | Do not open on a fire map. |
| 2 | Clock | Wall ⇄ sim toggle. America/Los_Angeles. HCRR 10 min named. | Two clocks, independent of any prompt. | Do not skip wall vs sim. |
| 3 | Wake | Network / curl: `/wake?case=frozen_a` + Pub/Sub published; optional `/health` eligibility (Gemini 3.7 · ADK · GCP). | Live gun path. No MAP_KEY. | Do not use EE FIRMS as live gun. |
| 4 | Frozen A | Quote card (TOM + PIO + FIRMS) · conjunction strip · MATCH · CLOSED_FIRE span · write log. | Reproducible currently-on-fire MATCH. | Do not hard-code a postmile set. |
| 5 | Write | TMCAL `write_happened: true` + HCRR row in write log / `/board`. | The board mutated. | Do not stop at a PDF or a map. |
| 6 | **`/reopen` in frame** | Address bar: `…/reopen/CA-1/PM12` → REFUSED + three quotes. Optional `?format=cert`. | Product URL, not a `/judges` toy. | Do not click a judges-only button and call it Reopen. |
| 7 | Frozen B | NON-MATCH · zero writes · `→ POST /reopen/CA-1/PM47 (ALLOWED)`. | Not a county webhook. | Do not skip. |
| 8 | **Live FIRMS GET** | Live pane strip shows real GET URL + row count. MATCH or honest empty. | U10 gun. Honest. | Do not backdate `acq_time`. Do not fake MATCH. |
| 9 | 404 pane | Unreachable paths 404. | We cannot impersonate the public SoR. | Do not demo a successful publish. |
| 10 | `/conformance` | 3/3 · `sor: firestore`. | LLM never decides MATCH. | Do not witness from Gemini text. |
| 11 | Console (D10) | GCP Console: Functions + Firestore / Pub/Sub / BQ or Armor. | Proof on Google Cloud. | Do not fake. Skip → D9, still ship. |
| 12 | Close | Closed postmiles + refused reopen still hold. Strip any map. | The TMCAL row and the refused Reopen are the product. | Do not close on "we mapped the fire." |

Unedited means: no jump-cuts that hide a failed MATCH, no dubbed overlay that claims a GET you did not do.

## Curl cheat-sheet (second monitor OK)

```powershell
$B="https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate"
curl.exe -sS "$B/health?format=json"
curl.exe -sS "$B/wake?case=frozen_a"
curl.exe -sS -X POST "$B/reopen/CA-1/PM12" -H "Content-Type: application/json" -d "{}"
curl.exe -sS "$B/reopen/CA-1/PM12?format=cert"
curl.exe -sS -X POST "$B/reopen/CA-1/PM47" -H "Content-Type: application/json" -d "{}"
curl.exe -sS "$B/wake?case=frozen_b"
curl.exe -sS --max-time 520 "$B/wake?case=live"
curl.exe -sS "$B/conformance?format=json"
curl.exe -sS -o NUL -w "%{http_code}" "$B/traveler-info"
curl.exe -sS "$B/llms.txt"
```
