"""Load D5 SHN GeoJSON into BigQuery as GEOGRAPHY."""

from __future__ import annotations

import json
from pathlib import Path

from google.cloud import bigquery

PROJECT = "all-things-agents-507211"
DATASET = "tmc_gate"
BASE = Path(__file__).resolve().parents[1] / "fixtures" / "shn"


def main() -> None:
    client = bigquery.Client(project=PROJECT)
    rows: list[dict] = []
    seen: set[tuple] = set()
    for name in ("d5_clip.geojson", "mon_ca1.geojson", "slo_ca1.geojson", "sb_ca1.geojson"):
        path = BASE / name
        if not path.exists():
            continue
        for feat in json.loads(path.read_text(encoding="utf-8")).get("features") or []:
            props = feat.get("properties") or {}
            geom = feat.get("geometry")
            if not geom:
                continue
            county = str(props.get("County") or "").upper()
            route = int(props.get("Route"))
            bpm = float(props.get("bPM"))
            epm = float(props.get("ePM"))
            key = (county, route, round(bpm, 3), round(epm, 3))
            if key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "county": county,
                    "route": route,
                    "bpm": bpm,
                    "epm": epm,
                    "geom_geojson": json.dumps(geom),
                }
            )

    ndjson_path = BASE / "shn_d5.ndjson"
    ndjson_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")

    staging = f"{PROJECT}.{DATASET}.shn_d5_staging"
    table_id = f"{PROJECT}.{DATASET}.shn_d5"
    client.delete_table(staging, not_found_ok=True)
    schema = [
        bigquery.SchemaField("county", "STRING"),
        bigquery.SchemaField("route", "INT64"),
        bigquery.SchemaField("bpm", "FLOAT64"),
        bigquery.SchemaField("epm", "FLOAT64"),
        bigquery.SchemaField("geom_geojson", "STRING"),
    ]
    client.create_table(bigquery.Table(staging, schema=schema))
    with ndjson_path.open("rb") as fh:
        client.load_table_from_file(
            fh,
            staging,
            job_config=bigquery.LoadJobConfig(
                source_format=bigquery.SourceFormat.NEWLINE_DELIMITED_JSON,
                schema=schema,
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
            ),
        ).result()

    sql = (
        f"CREATE OR REPLACE TABLE `{table_id}` AS "
        f"SELECT county, route, bpm, epm, ST_GeogFromGeoJSON(geom_geojson) AS geom "
        f"FROM `{staging}`"
    )
    client.query(sql).result()
    n = list(client.query(f"SELECT COUNT(*) AS n FROM `{table_id}`").result())[0].n
    print(f"loaded {n} rows into {table_id}")


if __name__ == "__main__":
    main()
