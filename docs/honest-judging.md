# Honest judging notes

- **U7 kill:** county-only closer. Guarded by `test_county_only_must_fail`.
- **U9:** `/reopen/{route}/{pm}` must work without `/judges`.
- **U10:** Live pane must GET real FIRMS 24h CSV (no MAP_KEY). Honest empty wake allowed.
- **A8:** Model Armor unavailable → print failed letter; do not silently skip (floor 88).
- **EE failure:** join cannot MATCH without NASADEM; do not close on intersect-only.
- **Conformance:** `/conformance` scores against Firestore objects, not Gemini prose.
- **Stdlib gate:** LLM quotes; BQ + EE decide MATCH. Named tests in `tests/test_join_gate.py` and `tests/test_api.py`.

Run:

```powershell
$env:TMC_STORE="memory"
$env:TMC_ADK_ORCHESTRATE="0"
pytest tests/ -v
```
