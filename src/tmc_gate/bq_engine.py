"""BigQuery ST_Intersects adapter + batch join helper."""

from __future__ import annotations

import os
from typing import Iterable

from shapely.geometry import Polygon

from tmc_gate.constants import LIVE_BQ_CHUNK
from tmc_gate.models import ShnSegment


class BqGeometryEngine:
    def __init__(self, project: str | None = None, dataset: str = "tmc_gate"):
        from google.cloud import bigquery

        self.project = project or os.environ.get("GOOGLE_CLOUD_PROJECT", "all-things-agents-507211")
        self.dataset = dataset
        self.client = bigquery.Client(project=self.project)
        self._job_id = None

    @property
    def job_id(self) -> str | None:
        return self._job_id

    def intersects(self, footprint: Polygon, segment: ShnSegment) -> bool:
        from google.cloud import bigquery

        job = self.client.query(
            """
            SELECT ST_Intersects(
              ST_GEOGFROMTEXT(@fp),
              ST_GEOGFROMTEXT(@shn)
            ) AS hit
            """,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("fp", "STRING", footprint.wkt),
                    bigquery.ScalarQueryParameter("shn", "STRING", segment.wkt),
                ]
            ),
        )
        self._job_id = job.job_id
        rows = list(job.result())
        return bool(rows and rows[0]["hit"])

    def intersecting_spans(
        self, footprints: Iterable[tuple[str, Polygon]]
    ) -> dict[str, list[tuple[str, int, float, float]]]:
        """Batch ST_Intersects against shn_d5. Returns firms_id -> [(county, route, bpm, epm)]."""
        from google.cloud import bigquery

        fps = list(footprints)
        if not fps:
            return {}
        out: dict[str, list[tuple[str, int, float, float]]] = {}
        table = f"`{self.project}.{self.dataset}.shn_d5`"
        chunk = max(1, int(LIVE_BQ_CHUNK))
        for offset in range(0, len(fps), chunk):
            batch = fps[offset : offset + chunk]
            parts = []
            params = []
            for i, (fid, poly) in enumerate(batch):
                parts.append(f"SELECT @fid{i} AS firms_id, ST_GEOGFROMTEXT(@wkt{i}) AS geom")
                params.append(bigquery.ScalarQueryParameter(f"fid{i}", "STRING", fid))
                params.append(bigquery.ScalarQueryParameter(f"wkt{i}", "STRING", poly.wkt))
            fps_sql = " UNION ALL ".join(parts)
            sql = f"""
            WITH fps AS ({fps_sql})
            SELECT f.firms_id, s.county, s.route, s.bpm, s.epm
            FROM fps f
            JOIN {table} s
            ON ST_Intersects(f.geom, s.geom)
            """
            job = self.client.query(sql, job_config=bigquery.QueryJobConfig(query_parameters=params))
            self._job_id = job.job_id
            for row in job.result():
                out.setdefault(row["firms_id"], []).append(
                    (row["county"], int(row["route"]), float(row["bpm"]), float(row["epm"]))
                )
        return out
