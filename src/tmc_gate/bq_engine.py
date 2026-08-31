"""BigQuery ST_Intersects adapter. Wired after hour-0. Local tests use ShapelyGeometryEngine."""

from __future__ import annotations

from tmc_gate.models import ShnSegment

ST_INTERSECTS_SQL = """
SELECT
  s.county, s.route, s.bpm, s.epm
FROM `{project}.{dataset}.shn_d5` s
WHERE ST_Intersects(
  ST_GEOGFROMWKT(@footprint_wkt),
  s.geom
)
AND s.county IN ('MON','SLO','SB','SCR','SBT')
"""


class BqGeometryEngine:
    def __init__(self, client, project: str, dataset: str = "tmc_gate"):
        self.client = client
        self.project = project
        self.dataset = dataset
        self._job_id = None

    @property
    def job_id(self) -> str | None:
        return self._job_id

    def intersects(self, footprint, segment: ShnSegment) -> bool:
        from google.cloud import bigquery

        job = self.client.query(
            """
            SELECT ST_Intersects(ST_GEOGFROMWKT(@fp), ST_GEOGFROMWKT(@shn)) AS hit
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
