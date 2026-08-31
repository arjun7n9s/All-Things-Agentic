# Contest submission checklist

Deadline: Mon 31 Aug 2026 5:00pm PDT · https://allthingsagentichackathon.devpost.com/

## Devpost fields

| Field | Value / artifact |
|---|---|
| Project name | Upslope (or Coast Range TMC) |
| Category | **The Taskmaster** |
| Hosted URL | https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate |
| Repo URL | https://github.com/arjun7n9s/All-Things-Agentic |
| Architecture diagram | `architecture.png` (upload) |
| Spin-up | README § Local spin-up + § GCP spin-up |
| Kill-if | README § Kill-if + `docs/kill-if.md` |
| Demo video | ~4 min public · `scripts/demo_shotlist.md` (1:1 with 12-demo-video) |
| Google SDK | Google ADK |
| Gemini model | gemini-3.7-flash (Vertex `global`, task-routed; floor 3.5) |

## Mandatory tech (DQ if missing)

- [x] **Gemini 3.5 or newer** — `gemini-3.7-flash` primary (+ `3.5` sheds) on Vertex AI (`global`), task-routed
- [x] **Google Agent Framework** — Google ADK (`LlmAgent` + `AgentTool` + `FunctionTool`)
- [x] **Google Cloud infrastructure** — Cloud Functions + Firestore + Pub/Sub + BQ + EE + Model Armor + Scheduler + Vertex
- [x] Track: **The Taskmaster**
- [x] Proof in `/health` → `eligibility` + `architecture.png` + hosted URL

## Floor gates (13-honest-judging)

- [x] `pytest tests/ -v` — 18 passed (incl. `test_county_only_must_fail`, `test_delete_ee_cannot_match`, `test_delete_bq_cannot_match`, `test_unreachable_404`, `test_reopen_refused_includes_quotes`, `test_conformance_3_of_3`, `test_no_cloud_run`)
- [x] Fixtures: `fixtures/shn/mon_ca1.geojson` (32 segments) + FIRMS 24h CSV
- [x] `/judges` three-quote card + conjunction strip + result + write log
- [x] Live pane fires real `/wake?case=live` GET every Live open
- [x] README kill-if block (Cloud Run not host)

## Repo hygiene

- [x] MIT LICENSE
- [x] `architecture.png` regenerated from `scripts/render_architecture.py`
- [x] `llms.txt` + `GET /llms.txt`
- [x] `SECURITY.md`
- [x] `docs/kill-if.md` + `docs/honest-judging.md`
- [x] `/reopen/{route}/{pm}?format=cert` refusal certificate
- [x] `.env.example` (no real keys; `GOOGLE_CLOUD_LOCATION=global`)
- [ ] Unedited ~4 min demo video uploaded
- [ ] Devpost text: features, technologies, data sources, findings
- [ ] Gallery 5–7 screenshots (Frozen A, Frozen B, Live, 404, conformance, reopen REFUSED, health)
- [ ] Optional: `#AllThingsAgenticHackathon` social / write-up

## Do not put in the public repo

- Spec pack occupancy names from `14-references.md`
- `.env` / API keys
- Co-authored-by lines that are not you
