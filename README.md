# tmc-gate â€” Coast Range TMC

When a satellite fire footprint is **upslope of this postmile**, write the TMC closure and **refuse Reopen**, before first shift.

Demo identity: **Coast Range TMC** (fixture TMC, D5-shaped SHN clip). Not Caltrans. Not a fire map.

Host: **Cloud Functions HTTP (2nd gen) + Cloud Storage**. Not Cloud Run. Not `.run.app`.

Contest: All Things Agentic [R1] Â· Taskmaster Â· Gemini 3.5+ Â· ADK `LlmAgent` + `AgentTool`.

---

## A10 claim

```
A10 claim: PENDING_ENABLE
Earth Engine: not-configured
Model Armor:  not-configured
```

If Earth Engine cannot enable: join **cannot MATCH**. Do not close on intersect-only.

If Model Armor cannot enable: **A8** (U10 / A8 / D8 = 88). Say so. Do not silently skip.

---

## Kill-if (we kill ourselves)

- County webhook (`Monterey â†’ close Hwy 1`) or a pre-parsed postmile `set`
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

- [http://127.0.0.1:8080/health](http://127.0.0.1:8080/health)
- [http://127.0.0.1:8080/judges](http://127.0.0.1:8080/judges) â€” stepper (Frozen A/B, live FIRMS GET, 404, clock, conformance)
- `POST http://127.0.0.1:8080/wake?case=frozen_a`
- `POST http://127.0.0.1:8080/reopen/CA-1/PM47` â€” product URL, not a `/judges` toy

Live pane GETs this morningâ€™s FIRMS CSV. Honest empty wake is allowed.

---

## GCP spin-up (after billing + keys)

See `scripts/hour0_enable.ps1`. Enable Earth Engine, BigQuery, Pub/Sub, Model Armor, Cloud Functions, Firestore, Secret Manager, Cloud Storage. Register the project for Earth Engine:

`https://code.earthengine.google.com/register?project=PROJECT_ID`

Put the Gemini key in Secret Manager (`gemini-api-key`). Do not mint user-managed service-account JSON keys. Do not put keys in git.

Deployable is a **2nd gen HTTP Cloud Function** named `tmc-gate` with entry `tmc_gate`. Static `/judges` may be copied to Cloud Storage. **Do not deploy Cloud Run.**

---

## Join (stdlib, not LLM)

Gemini **quotes** TOM Chapter 110 (HCRR 10 min; county, route, and post mile; steep slope above the highway) and FIRMS `acq_time` / confidence / FRP / satellite.

Stdlib **conjuncts**:

1. Confidence âˆˆ {nominal, high} (VIIRS)
2. Native VIIRS footprint `ST_Intersects` a D5 SHN segment (BigQuery in production; Shapely locally)
3. NASADEM `z_hotspot > z_shn` (Earth Engine in production; fixture sampler locally)
4. Route on the D5 clip

Either engine missing â†’ `CAN'T READ`, not MATCH. County-only **must fail**.

Probed FIRMS 24h KML is Point placemarks. Native geometry is the sensor pixel from CSV `scan`Ã—`track` (~375 m), **not** an invented 100-foot buffer.

---

## Architecture

See `architecture.png` (and `04-architecture.md` in the spec pack). Load-bearing: Earth Engine NASADEM, BigQuery `ST_Intersects`, Pub/Sub, Model Armor fail-closed, Functions + Storage, Firestore TMCAL, Secret Manager, ADK quotes-only.

---

## Tests

Named stdlib-gate tests in `tests/`. Do not claim 320.

---

## License

MIT. See `LICENSE`.

## Hosted URL (Google Cloud Functions)

Use this URL only (Cloud Functions), never the underlying `.run.app`:

https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate

- Judges UI: https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate/judges
- Health: https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate/health
- Product reopen: `POST .../reopen/CA-1/PM12`

A10 claim: Earth Engine + Model Armor + BigQuery enabled on `all-things-agents-507211`.

