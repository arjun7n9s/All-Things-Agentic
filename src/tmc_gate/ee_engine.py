"""Earth Engine NASADEM sampler. Wired after hour-0. Do not use EE FIRMS as the live gun."""

from __future__ import annotations

from tmc_gate.constants import NASADEM_ID
from tmc_gate.models import ElevationSample, FirmsDetection, ShnSegment


class EeNasademEngine:
    def __init__(self, project: str):
        self.project = project
        self._job_id = None

    def sample(self, det: FirmsDetection, segment: ShnSegment) -> ElevationSample:
        import ee

        ee.Initialize(project=self.project)
        img = ee.Image(NASADEM_ID).select("elevation")
        z_hot = img.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=ee.Geometry.Point([det.longitude, det.latitude]),
            scale=30,
        ).get("elevation")
        # Nearest SHN vertex: use centroid of the intersecting segment as stand-in
        coords = list(segment.geometry.centroid.coords)[0]
        z_shn = img.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=ee.Geometry.Point([coords[0], coords[1]]),
            scale=30,
        ).get("elevation")
        info = ee.Dictionary({"h": z_hot, "s": z_shn}).getInfo()
        self._job_id = "ee-nasadem"
        return ElevationSample(
            z_hotspot=float(info["h"]),
            z_shn=float(info["s"]),
            ee_job_id=self._job_id,
        )
