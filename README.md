# tmc-gate — Coast Range TMC

When a satellite fire footprint is **upslope of this postmile**, write the TMC closure and **refuse Reopen**, before first shift.

Demo identity: **Coast Range TMC** (fixture TMC, D5-shaped SHN clip). Not Caltrans. Not a fire map.

Host: **Cloud Functions HTTP (2nd gen)**. Not Cloud Run. Not `.run.app`.

Contest: All Things Agentic · Taskmaster · Gemini · ADK `LlmAgent` + `AgentTool`.

---

## A10 claim

```
A10 claim: ENABLED
Earth Engine: enabled (NASADEM upslope)
BigQuery:     enabled (ST_Intersects)
Pub/Sub:      enabled (firms-batches + firms-ee-tasks)
Model Armor:  enabled (fail-closed)
Firestore:   enabled (TMCAL SoR)
Secret Manager / Cloud Storage: enabled
```

If Earth Engine cannot enable: join **cannot MATCH**. Do not close on intersect-only.

If Model Armor cannot enable: **A8** (U10 / A8 / D8 = 88). Say so. Do not silently skip.

---

## Kill-if (we kill ourselves)

- County webhook (`Monterey → close Hwy 1`) or a pre-parsed postmile `set`
- The artifact is a fire map; strip the map and nothing remains
- `/reopen` lives only on `/judges`
- Cloud Run / `.run.app` as the host
- Email
- Invented 100-ft / 30-m buffer (native VIIRS pixel, or CAN'T READ)
- EE FIRMS catalog as the live gun (1-day lag). Live gun is FIRMS 24h CSV+KML, no MAP_KEY
- MATCH from LLM output / `eval` of Gemini text
- Publish traveler-info or write CAD
- Real employee names, real CAD incidents
- Silently skip Earth Engine or Model Armor

---

## Hosted URL (Cloud Functions only)

https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate

| Path | Role |
|---|---|
| `/judges` | Stepper (Frozen A/B, live FIRMS, 404, clock, conformance) |
| `/health` | Enablement letters |
| `/wake?case=frozen_a` | Currently-on-fire MATCH |
| `/wake?case=frozen_b` | Inland NON-MATCH (not a county webhook) |
| `/wake?case=live` | This morning's FIRMS CSV |
| `POST /reopen/CA-1/PM12` | Product URL — REFUSED while Frozen A span is CLOSED_FIRE |
| `POST /reopen/CA-1/PM47` | Valid product URL — ALLOWED unless *that* span is CLOSED_FIRE |
| `/conformance` | 3/3 against Firestore objects |

Demo film shot list: `scripts/demo_shotlist.md`.

---

## Local spin-up (no GCP keys)

Python 3.11+. From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
$env:FUNCTION_TARGET="tmc_gate"
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

See `scripts/hour0_enable.ps1`. Enable Earth Engine, BigQuery, Pub/Sub, Model Armor, Cloud Functions, Firestore, Secret Manager, Cloud Storage. Register the project for Earth Engine.

Put the Gemini key in Secret Manager (`gemini-api-key`). Do not mint user-managed service-account JSON keys. Do not put keys in git.

Deployable is a **2nd gen HTTP Cloud Function** named `tmc-gate` with entry `tmc_gate`. **Do not deploy Cloud Run.**

Overnight live wake (optional Cloud Scheduler → Functions HTTPS):

```powershell
gcloud scheduler jobs create http tmc-gate-overnight-live `
  --location=us-central1 `
  --schedule="15 * * * *" `
  --time-zone="America/Los_Angeles" `
  --uri="https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate/wake?case=live" `
  --http-method=GET `
  --attempt-deadline=540s
```

---

## Join (stdlib, not LLM)

Gemini **quotes** TOM Chapter 110 (HCRR 10 min; county, route, and post mile; steep slope above the highway) and FIRMS `acq_time` / confidence / FRP / satellite via ADK `LlmAgent` + `AgentTool`.

Stdlib **conjuncts**:

1. Confidence ∈ {nominal, high} (VIIRS)
2. Native VIIRS footprint `ST_Intersects` a D5 SHN segment (BigQuery in production; Shapely locally)
3. NASADEM `z_hotspot > z_shn` (Earth Engine in production; fixture sampler locally)
4. Route on the D5 clip

Either engine missing → `CAN'T READ`, not MATCH. County-only **must fail**.

Probed FIRMS 24h KML is Point placemarks. Native geometry is the sensor pixel from CSV `scan`×`track` (~375 m), **not** an invented 100-foot buffer.

---

## Architecture

See `architecture.png`. Load-bearing: Earth Engine NASADEM, BigQuery `ST_Intersects`, Pub/Sub, Model Armor fail-closed, Functions, Firestore TMCAL, Secret Manager, ADK quotes-only.

---

## Tests

Named stdlib-gate tests in `tests/`. Do not claim 320.

```powershell
pytest
```

---

## License

MIT. See `LICENSE`.
