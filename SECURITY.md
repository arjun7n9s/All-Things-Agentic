# Security

- Do not commit `.env`, API keys, or service-account JSON.
- Prefer Vertex AI ADC on Cloud Functions; optional Gemini key lives in Secret Manager (`gemini-api-key`).
- Model Armor screens quote prose fail-closed. Earth Engine / Armor failures must be printed on `/health` — never silently skipped.
- Report vulnerabilities privately to the repo owner; do not open public issues that contain secrets.
