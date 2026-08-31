# tmc-gate — Coast Range TMC

When a satellite fire footprint is **upslope of this postmile**, write the TMC closure and **refuse Reopen**, before first shift.

Demo identity: **Coast Range TMC** (fixture TMC, D5-shaped SHN clip). Not Caltrans. Not a fire map. **Not a chatbot.**

Host: **Cloud Functions HTTP (2nd gen)** at `cloudfunctions.net`. Not advertised as Cloud Run / `.run.app`.

Contest: **All Things Agentic · The Taskmaster**.

---

## Hackathon eligibility (mandatory stack)

Every project must use Gemini 3.5+, one Google Agent Framework, and one Google Cloud infrastructure service. This repo uses all three:

| Requirement | What tmc-gate uses |
|---|---|
| **Gemini 3.5 or newer** via Gemini API or Vertex AI | **`gemini-3.7-flash` on Vertex AI** (`GOOGLE_CLOUD_LOCATION=global`), with task-scoped routing |
| **Google Agent Framework** | **Google ADK** — `LlmAgent` + `AgentTool` + `FunctionTool` |
| **Google Cloud infrastructure** | **Cloud Functions**, **Firestore**, **Pub/Sub**, **BigQuery**, **Earth Engine**, **Model Armor**, **Secret Manager**, **Cloud Storage**, **Cloud Scheduler**, **Vertex AI** |

### Gemini model routing (architectural)

| Task | Model | Why |
|---|---|---|
| Overnight parent agent | `gemini-3.7-flash` | Agentic workhorse — multi-step FunctionTool orchestration |
| Overnight 429 shed | `gemini-3.5-flash` | Same ADK tools if Vertex rate-limits 3.7 |
| Quote clerk (AgentTool) | `gemini-3.7-flash` | Instruction-faithful TOM / PIO / FIRMS verbatim quotes |
| Quote retry shed | `gemini-3.5-flash` | Stay ≥ mandatory 3.5 floor if primary fails |
| Lite probe (optional) | `gemini-3.1-flash-lite` | Cheap non-decision traffic only |
| Last resort | Deterministic FunctionTool pipeline | Identical tools; no invented MATCH |
| MATCH / NON-MATCH | **stdlib** (BQ + EE) | LLM never decides MATCH |

Implemented in `src/tmc_gate/model_router.py`. Exposed on `GET /health` → `eligibility.gemini_routing`.

Proof surfaces:

- `GET /health` → `eligibility` object (model routing, ADK, GCP services)
- `architecture.png` (upload this on Devpost)
- Hosted URL below (highly encouraged for judging)

Track fit (**Taskmaster**): overnight wake is an event-driven workflow — fetch FIRMS → quote TOM → BQ/EE join → write TMCAL/HCRR → refuse `/reopen` — without a chat loop.

---

## A10 claim

```
A10 claim: ENABLED
Gemini:       gemini-3.7-flash primary (Vertex AI, location=global; quote_retry=3.5)
ADK:          LlmAgent + AgentTool + FunctionTools
Earth Engine: enabled (NASADEM upslope)
BigQuery:     enabled (ST_Intersects)
Pub/Sub:      enabled (firms-batches + firms-ee-tasks)
Model Armor:  enabled (fail-closed)
Firestore:   enabled (TMCAL SoR)
Secret Manager / Cloud Storage / Cloud Functions / Scheduler: enabled
```

If Earth Engine cannot enable: join **cannot MATCH**. Do not close on intersect-only.

If Model Armor cannot enable: **A8** (U10 / A8 / D8 = 88). Say so. Do not silently skip.

---

## Kill-if (we kill ourselves)

Tripwire list (also in [`docs/kill-if.md`](docs/kill-if.md); honest-judging notes in [`docs/honest-judging.md`](docs/honest-judging.md)):

- County webhook (`Monterey → close Hwy 1`) or a pre-parsed postmile `set`
- The artifact is a fire map; strip the map and nothing remains
- `/reopen` lives only on `/judges`
- Cloud Run / `.run.app` as the advertised host
- Email
- Invented 100-ft / 30-m buffer (native VIIRS pixel, or CAN'T READ)
- EE FIRMS catalog as the live gun (1-day lag). Live gun is FIRMS 24h CSV+KML, no MAP_KEY
- MATCH from LLM output / `eval` of Gemini text
- Publish traveler-info or write CAD
- Real employee names, real CAD incidents
- Silently skip Earth Engine or Model Armor
- Gemini model older than 3.5 as the production quote / overnight path
- County-only closer (`test_county_only_must_fail` must catch this)
- Join still MATCHes after deleting BQ or EE

---

## Hosted URL (Cloud Functions)

https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate

| Path | Role |
|---|---|
| `/judges` | Stepper (Frozen A/B, live FIRMS, 404, conformance) |
| `/health` | Enablement letters + eligibility JSON |
| `/wake?case=frozen_a` | Currently-on-fire MATCH |
| `/wake?case=frozen_b` | Inland NON-MATCH (not a county webhook) |
| `/wake?case=live` | This morning's FIRMS CSV |
| `POST /reopen/CA-1/PM12` | Product URL — REFUSED while Frozen A span is CLOSED_FIRE |
| `POST /reopen/CA-1/PM47` | Valid product URL — ALLOWED unless *that* span is CLOSED_FIRE |
| `/conformance` | 3/3 against Firestore objects |
| `/reopen/…?format=cert` | Refusal / allow certificate (manifest + hashes) |
| `/llms.txt` | Machine-readable endpoint map |

Demo film shot list (1:1 with demo-video spec): `scripts/demo_shotlist.md`. Submission checklist: `scripts/submission_checklist.md`. Machine map: `llms.txt`.

---

## Local spin-up (no GCP keys)

Python 3.11+. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
$env:FUNCTION_TARGET="tmc_gate"
$env:TMC_ADK_ORCHESTRATE="0"
functions-framework --target=tmc_gate --source=main.py --debug --port=8080
```

Then:

- http://127.0.0.1:8080/health
- http://127.0.0.1:8080/judges
- `POST http://127.0.0.1:8080/wake?case=frozen_a`
- `POST http://127.0.0.1:8080/reopen/CA-1/PM12` — product URL, not a `/judges` toy

Live pane GETs this morning's FIRMS CSV. Honest empty wake is allowed.

---

## GCP spin-up (after billing + keys)

See `scripts/hour0_enable.ps1`. Enable Earth Engine, BigQuery, Pub/Sub, Model Armor, Cloud Functions, Firestore, Secret Manager, Cloud Storage, Vertex AI. Register the project for Earth Engine.

**Gemini 3.7 / 3.5 on Vertex require `GOOGLE_CLOUD_LOCATION=global`.** Model Armor stays regional (`MODEL_ARMOR_LOCATION=us-central1`).

Put optional Gemini API key in Secret Manager (`gemini-api-key`). Prefer Vertex ADC on Cloud Functions. Do not mint user-managed service-account JSON keys. Do not put keys in git.

Deployable is a **2nd gen HTTP Cloud Function** named `tmc-gate` with entry `tmc_gate`. Advertise the `cloudfunctions.net` URL, not `.run.app`.

Overnight live wake (Cloud Scheduler → Functions HTTPS):

```powershell
gcloud scheduler jobs create http tmc-gate-overnight-live `
  --location=us-central1 `
  --schedule="15 * * * *" `
  --time-zone="America/Los_Angeles" `
  --uri="https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate/wake?case=live&source=scheduler" `
  --http-method=GET `
  --attempt-deadline=540s
```

---

## Join (stdlib, not LLM)

Gemini 3.7 Flash (ADK, task-routed) **quotes** TOM Chapter 110 (HCRR 10 min; county, route, and post mile; steep slope above the highway) and FIRMS `acq_time` / confidence / FRP / satellite.

Stdlib **conjuncts**:

1. Confidence ∈ {nominal, high} (VIIRS)
2. Native VIIRS footprint `ST_Intersects` a D5 SHN segment (BigQuery in production; Shapely locally)
3. NASADEM `z_hotspot > z_shn` (Earth Engine in production; fixture sampler locally)
4. Route on the D5 clip

Either engine missing → `CAN'T READ`, not MATCH. County-only **must fail**.

Probed FIRMS 24h KML is Point placemarks. Native geometry is the sensor pixel from CSV `scan`×`track` (~375 m), **not** an invented 100-foot buffer.

---

## Architecture

See [`architecture.png`](architecture.png) (upload this on Devpost).

Flow: **FIRMS / Scheduler → desk UI (`/judges`) → Cloud Functions → Gemini 3.7 + Google ADK (quotes only) → BigQuery ∩ Earth Engine → stdlib gate → Firestore TMCAL → `/reopen` + `/conformance`.**

Load-bearing: Gemini 3.5+ via ADK quotes-only (never MATCH), Earth Engine NASADEM, BigQuery `ST_Intersects`, Pub/Sub, Model Armor fail-closed, Cloud Functions host (`cloudfunctions.net`, not `.run.app`), Firestore TMCAL, Secret Manager.

---

## Technologies used (Devpost write-up)

- **Gemini 3.7 Flash** (primary) + **3.5 Flash** (quote retry) via **Vertex AI** (`global`), task-routed
- **Google ADK** (`google-adk`) — overnight `LlmAgent` orchestrates real `FunctionTool`s
- **Cloud Functions** (HTTP 2nd gen) — product host
- **Firestore** — TMCAL system of record
- **Pub/Sub** — FIRMS wake witness
- **BigQuery** — `ST_Intersects` join
- **Earth Engine** — NASADEM upslope
- **Model Armor** — fail-closed prompt screening
- **Secret Manager**, **Cloud Storage**, **Cloud Scheduler**
- Data: NOAA FIRMS 24h CSV/KML (no MAP_KEY), Caltrans SHN FeatureServer clip (fixture D5), TOM Ch 110 packet

---

## Reproducible testing

Named stdlib-gate tests in `tests/test_join_gate.py` and `tests/test_api.py`. Do not claim hundreds of tests — claim the load-bearing ones.

### Local (no GCP keys, deterministic)

Python 3.11+. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"

# Force in-memory SoR + fixture engines. Do not hit live Vertex / EE / Firestore.
$env:TMC_STORE = "memory"
$env:TMC_FIRESTORE = ""
$env:TMC_EARTH_ENGINE = ""
$env:TMC_ADK_ORCHESTRATE = "0"
$env:GOOGLE_API_KEY = ""
$env:GEMINI_API_KEY = ""

python -m pytest tests/ -v
```

Expected: **all tests pass** (currently 22). Load-bearing names a judge can grep:

| Test | Why it exists |
|---|---|
| `test_county_only_must_fail` | U7 kill — not a Monterey webhook |
| `test_delete_ee_cannot_match` | NASADEM missing → no MATCH |
| `test_delete_bq_cannot_match` | `ST_Intersects` missing → no MATCH |
| `test_no_invented_100ft_buffer` | Native VIIRS pixel only |
| `test_reopen_refused_includes_quotes` | Product URL + three quotes |
| `test_reopen_pm47_not_county_webhook` | PM47 ALLOWED after Frozen A |
| `test_conformance_3_of_3` | Scores Firestore/memory objects |
| `test_unreachable_404` | traveler-info / CAD / email 404 |
| `test_no_cloud_run` | Host is Functions, not `.run.app` |
| `test_board_dedupes_same_span` | One TMCAL row per SHN span |
| `test_refusal_certificate` | `?format=cert` hashes |
| `test_desk_html_surfaces` | SSR first paint on `/judges` |

### Reproduce the film URLs locally

```powershell
$env:FUNCTION_TARGET = "tmc_gate"
$env:TMC_STORE = "memory"
$env:TMC_ADK_ORCHESTRATE = "0"
functions-framework --target=tmc_gate --source=main.py --debug --port=8080
```

In another shell:

```powershell
curl.exe -sS -X POST "http://127.0.0.1:8080/wake?case=frozen_a"
curl.exe -sS -X POST "http://127.0.0.1:8080/reopen/CA-1/PM12"   # REFUSED
curl.exe -sS -X POST "http://127.0.0.1:8080/reopen/CA-1/PM47"   # ALLOWED
curl.exe -sS "http://127.0.0.1:8080/conformance?format=json"    # 3/3
curl.exe -sS "http://127.0.0.1:8080/reopen/CA-1/PM12?format=cert"
curl.exe -sS -o NUL -w "%{http_code}" "http://127.0.0.1:8080/traveler-info"  # 404
```

### Hosted smoke (optional)

```powershell
$B = "https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate"
curl.exe -sS "$B/health?format=json"
curl.exe -sS "$B/wake?case=frozen_a"
curl.exe -sS -X POST "$B/reopen/CA-1/PM12"
curl.exe -sS "$B/conformance?format=json"
```

If any kill-if trips (county-only closer, Cloud Run advertised, EE skipped silently), print the failed letter — do not ship a green CI by deleting the test.

---

## License

MIT. See `LICENSE`.
