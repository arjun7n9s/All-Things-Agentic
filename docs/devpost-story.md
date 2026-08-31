# Upslope — Devpost Project Story

Paste the sections below into Devpost. Track: **The Taskmaster**. Hosted URL: `https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate` (not `.run.app`). Upload `architecture.png`.

---

## About the project

Overnight, a coastal TMC is dark. The analog already closed Highway 1 where crews could see the fire. What they cannot do, postmile by postmile, while the desk is empty, is ask: *is a satellite footprint still sitting on the slope above this traveled way — and if so, may anyone reopen it?*

**Upslope** is that leftover job. It is a fixture desk named Coast Range TMC (D5-shaped SHN clip). Not Caltrans. Not a chatbot. Not a wildfire map. If you strip the map, the product that remains is a Firestore TMCAL row (`OPEN → CLOSED_FIRE`) and a product URL that **refuses reopen** while FIRMS is still upslope.

### Inspiration

Highway-condition duty is conjunction, not vibe. Traffic Operations Manual Chapter 110 already says the hard parts in prose: report **county, route, and post mile**; HCRR within **10 minutes** of a full/directional closure; close when the roadway is not passable. PIO language for this corridor talks about **falling rock from the steep slope above the highway**. NASA already detected the heat. The overnight dispatcher does not need another map. They need a write that survives first shift, and a reopen that cannot be rubber-stamped while the slope is still hot.

The occupied work is “there is a fire, close Hwy 1.” The unoccupied slice is: **this postmile is still `CLOSED_FIRE`; `POST /reopen/CA-1/PM12` is REFUSED**, with the three quotes still attached (`acq_time`, SHN span, $z_\Delta$).

### How we built it

The overnight wake is an event-driven ADK workflow, not a chat loop:

1. **Gun.** GET NOAA FIRMS 24h CSV + KML (no `MAP_KEY`). Live gun is that feed — not the Earth Engine FIRMS catalog (one-day lag). Frozen A/B replay against live SHN bytes; the Live pane GETs **this morning’s** CSV every time it opens. Honest empty is allowed.
2. **Quotes, never MATCH.** A Gemini 3.7 Flash `LlmAgent` (Vertex AI, `GOOGLE_CLOUD_LOCATION=global`) orchestrates `FunctionTool`s. A nested quote clerk (AgentTool) returns verbatim TOM / FIRMS strings — or `CAN'T READ`. On 429 we shed to Gemini 3.5 Flash. Same tools. MATCH still cannot come from the model.
3. **Stdlib conjunction.** Python decides MATCH. Gemini’s output is never `eval`’d.

$$
\text{MATCH} = C_{\{\text{nominal},\text{high}\}} \;\land\; \operatorname{ST\_Intersects}(F,S) \;\land\; (z_{\text{hotspot}} > z_{\text{SHN}}) \;\land\; R \in D5
$$

Native geometry is the VIIRS pixel from CSV `scan` × `track` (~375 m). We do **not** invent a 100-ft buffer. BigQuery owns intersect; Earth Engine NASADEM owns upslope. Delete either engine → `CAN'T READ`, not MATCH. County-only (`Monterey → close Hwy 1`) **must fail** (`test_county_only_must_fail`).

4. **Write.** Firestore TMCAL mutation + HCRR draft row (`write_happened: true`) + Pub/Sub witness. `/conformance` scores **3/3 against Firestore objects**, not against Gemini prose.
5. **Reopen-gate.** `POST /reopen/{route}/{pm}` is a product URL, not a `/judges` toy. Frozen A span (honest PM12) → REFUSED + three quotes. PM47 after Frozen A → ALLOWED (proves we are not a county webhook). `?format=cert` returns a refusal certificate (manifest hash, outcome hash, quotes).
6. **Unreachable on purpose.** Traveler-info, CAD, email, cone, blast: **404**. Tool schema does not contain them.

Host is **2nd gen Cloud Functions** (`cloudfunctions.net`). We do not advertise Cloud Run / `.run.app`. Model Armor is fail-closed and regional (`us-central1`); Gemini routing stays `global`. Credentials live in Secret Manager / ADC — no user-managed JSON keys in git.

Judge surfaces: `/judges` (Frozen A / Frozen B / Live / 404 / conformance), `/health` (eight enablement letters + eligibility), `/reopen/...`, `/conformance`, `/llms.txt`.

### What we learned

- **Quote ≠ decide.** If MATCH can be parsed out of an LLM string, the architecture is already a cheat. ADK is the overnight clerk; BigQuery + Earth Engine + stdlib are the closer.
- **Occupancy is a scoring kill.** “AI wildfire map” and “county webhook” look demo-friendly and score as U7. The product is the refused reopen.
- **Fail closed, print the letter.** Earth Engine down → no MATCH (do not close on intersect-only). Armor down → print A8; do not silently skip. Gemini older than 3.5 on the overnight/quote path is a DQ, not a fallback.
- **Dense live field beats sparse luck.** Frozen A proves currently-on-fire; Frozen B proves inland pixels are not the traveled way; Live proves the gun is this morning’s CSV.

### Challenges

Vertex `gemini-3.7-flash` 429s under ADK tool loops. The honest fix is a 3.5 Flash shed on the **same FunctionTools**, then a deterministic tool pipeline — never a cheaper model inventing MATCH.

Earth Engine registration is hour-0, not polish: without NASADEM the upslope conjunct cannot run, and the U7 county-closer temptation appears. We enable EE first (`scripts/hour0_enable.ps1`) and keep a named test that fails the build if county-only ships.

FIRMS KML is Point placemarks. Using those points plus an invented buffer would be a kill-if. CSV `scan`×`track` is the native pixel; that is the geometry BQ intersects.

The UI temptation is a map. The desk is dark `#0b0b0c`, typography-as-state, three-quote card, conjunction strip, write log — zero chat. A map, if it exists, is a receipt.

### Links

- Hosted (advertise this): https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate
- Repo: https://github.com/arjun7n9s/All-Things-Agentic
- Kill-if (we kill ourselves): README + `docs/kill-if.md`

---

## Built with

Devpost tags (14 — do not pad to 25):

1. Python
2. Google Cloud
3. Vertex AI
4. Gemini
5. Google ADK
6. Cloud Functions
7. Firestore
8. BigQuery
9. Google Pub/Sub
10. Google Earth Engine
11. Model Armor
12. Secret Manager
13. Cloud Storage
14. Cloud Scheduler

If the catalog lacks **Google ADK** or **Model Armor**, add them as custom tags.
