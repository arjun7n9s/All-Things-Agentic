# Kill-if (judge-facing)

Full tripwire list for this product. If any line is true, we kill the claim — we do not silently skip.

1. County webhook (`Monterey → close Hwy 1`) or a pre-parsed postmile `set`
2. The artifact is a fire map; strip the map and nothing remains
3. `/reopen` lives only on `/judges` (not a product URL)
4. Cloud Run / `.run.app` as the advertised host
5. Email
6. Invented 100-ft / 30-m buffer (native VIIRS pixel, or CAN'T READ)
7. EE FIRMS catalog as the live gun (1-day lag). Live gun is FIRMS 24h CSV+KML, no MAP_KEY
8. MATCH from LLM output / `eval` of Gemini text
9. Publish traveler-info or write CAD
10. Real employee names, real CAD incidents
11. Silently skip Earth Engine or Model Armor (print the failed A letter)
12. County-only closer ships (`test_county_only_must_fail` must catch this)
13. Join still MATCHes after deleting BQ `ST_Intersects` or EE NASADEM
14. Gemini older than 3.5 on the production quote / overnight path

See also `README.md` § Kill-if and `docs/honest-judging.md`.
