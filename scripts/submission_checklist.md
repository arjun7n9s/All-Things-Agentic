# Contest submission checklist

Deadline: Mon 31 Aug 2026 5:00pm PDT · https://allthingsagentichackathon.devpost.com/

## Mandatory tech (DQ if missing)

- [x] **Gemini 3.5 or newer** — `gemini-3.5-flash` on Vertex AI (`GOOGLE_CLOUD_LOCATION=global`)
- [x] **Google Agent Framework** — Google ADK (`LlmAgent` + `AgentTool` + `FunctionTool`)
- [x] **Google Cloud infrastructure** — Cloud Functions + Firestore + Pub/Sub + BQ + EE + Model Armor + Scheduler + Vertex
- [x] Track selected: **The Taskmaster** (action workflow, not chat)
- [x] Proof in `/health` → `eligibility` + `architecture.png` + hosted URL

## Repo / Devpost fields

- [x] Public GitHub product repo (no `.run.app` as advertised host)
- [x] MIT LICENSE
- [x] `architecture.png` (upload on Devpost)
- [x] Spin-up instructions in README (local + GCP)
- [x] Kill-if + A10 + eligibility table in README
- [x] Stdlib-gate tests (`pytest`)
- [ ] Unedited ~4 min demo video uploaded (see `demo_shotlist.md`)
- [ ] Devpost text: features, technologies, data sources, findings/learnings
- [ ] Disclose pre-existing / third-party code used
- [ ] Answer which Google SDK (ADK) + project start date
- [ ] Optional bonus: public write-up / social `#AllThingsAgenticHackathon` / Gemma·Veo·Lyria

## Hosted proof

- [x] Cloud Functions URL: https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate
- [x] `/judges` dark desk stepper
- [x] `/reopen/CA-1/PM12` product URL REFUSED after Frozen A
- [x] `/conformance` 3/3 with `sor: firestore`
- [x] Pub/Sub publish on wake + overnight Scheduler job `tmc-gate-overnight-live`
- [x] ADK + Gemini 3.5 on production wake path

## Film must show (under 4 min)

1. `/judges` working in first 10–15s (not a map lead)
2. Wall vs sim clock
3. Frozen A → MATCH / CLOSED_FIRE write log
4. Address bar `…/reopen/CA-1/PM12` → REFUSED + three quotes
5. Frozen B zero writes / not county webhook (PM47 ALLOWED)
6. Live FIRMS GET strip (honest empty OK)
7. 404 unreachable paths
8. `/conformance` 3/3
9. **GCP proof**: Cloud Functions URL bar + Console (Vertex / Firestore / Pub/Sub / Armor) — required by rules

## Do not put in the public repo

- Spec pack / `14-references.md`
- `.env` / API keys
- Co-authored-by lines that are not you
