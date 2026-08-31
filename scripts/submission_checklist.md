# Contest submission checklist

Deadline: Mon 31 Aug 2026 5:00pm PDT.

## Repo

- [x] GitHub product repo (no `.run.app` as host)
- [x] MIT LICENSE
- [x] `architecture.png`
- [x] Kill-if + A10 in README
- [x] Stdlib-gate tests (`pytest` — 17)
- [ ] Unedited ~4 min demo video uploaded (see `demo_shotlist.md`)

## Hosted proof

- [x] Cloud Functions URL: https://us-central1-all-things-agents-507211.cloudfunctions.net/tmc-gate
- [x] `/judges` stepper
- [x] `/reopen/CA-1/PM12` product URL REFUSED after Frozen A
- [x] `/conformance` 3/3 with `sor: firestore`
- [x] Pub/Sub publish on wake + overnight Scheduler job `tmc-gate-overnight-live`
- [x] ADK quotes on production wake (`adk_quotes: true`)

## Film must show

1. `/judges` (not a map lead)
2. Wall vs sim clock
3. Frozen A wake → board CLOSED_FIRE
4. Address bar `…/reopen/CA-1/PM12` → REFUSED + quotes
5. Frozen B zero writes / not county webhook
6. Live FIRMS GET (honest empty OK)
7. 404 unreachable
8. `/conformance` 3/3
9. Optional: GCP Console (BQ / Pub/Sub / Firestore / Armor)

## Do not put in the public repo

- Spec pack / `14-references.md`
- `.env` / API keys
- Co-authored-by lines that are not you
