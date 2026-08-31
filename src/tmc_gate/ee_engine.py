"""Earth Engine NASADEM sampler. Live gun is FIRMS CSV/KML — not EE FIRMS."""

from __future__ import annotations

import os

from tmc_gate.constants import NASADEM_ID
from tmc_gate.firms import native_pixel_polygon
from tmc_gate.models import ElevationSample, FirmsDetection, ShnSegment


class EeNasademEngine:
    def __init__(self, project: str | None = None):
        self.project = project or os.environ.get("GOOGLE_CLOUD_PROJECT", "all-things-agents-507211")
        self._job_id = None
        self._ready = False

    def _init(self) -> None:
        if self._ready:
            return
        import ee

        ee.Initialize(project=self.project)
        self._ready = True

    def sample(self, det: FirmsDetection, segment: ShnSegment) -> ElevationSample:
        import ee

        self._init()
        img = ee.Image(NASADEM_ID).select("elevation")
        # Max elev inside the native VIIRS footprint (coastal pixels can straddle water=0).
        fp = native_pixel_polygon(det)
        ring = [list(c) for c in fp.exterior.coords]
        footprint = ee.Geometry.Polygon([ring])
        z_hot = img.reduceRegion(reducer=ee.Reducer.max(), geometry=footprint, scale=30, maxPixels=1e6).get(
            "elevation"
        )
        # Nearest SHN vertex to the detection.
        from shapely.ops import nearest_points

        _, shn_pt = nearest_points(fp.centroid, segment.geometry)
        lon, lat = shn_pt.x, shn_pt.y
        z_shn = img.reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=ee.Geometry.Point([lon, lat]),
            scale=30,
        ).get("elevation")
        info = ee.Dictionary({"h": z_hot, "s": z_shn}).getInfo()
        self._job_id = "ee-nasadem"
        h = info.get("h")
        s = info.get("s")
        if h is None or s is None:
            raise RuntimeError("nasadem_sample_missing")
        return ElevationSample(z_hotspot=float(h), z_shn=float(s), ee_job_id=self._job_id)
