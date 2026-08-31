"""FIRMS 24h CSV + KML poller. No MAP_KEY. Not Earth Engine FIRMS."""

from __future__ import annotations

import csv
import io
import math
import urllib.request
from pathlib import Path

from shapely.geometry import Polygon

from tmc_gate.constants import D5_BBOX, FIRMS_CSV, FIRMS_KML
from tmc_gate.models import FirmsDetection

# VIIRS native pixel is ~375 m. scan/track in the CSV are that pixel, in km.
# This is the sensor footprint. It is NOT an invented 100-ft / 30-m buffer.
_FT100_M = 30.48  # referenced only to FORBID using it as a buffer.


def live_gun_urls() -> dict[str, str]:
    return {"csv": FIRMS_CSV["noaa20"], "kml": FIRMS_KML["noaa20"]}


def is_ee_firms_url(url: str) -> bool:
    u = url.lower()
    return "imagecollection" in u or u.endswith("/firms") or "earthengine.googleapis.com" in u


def fetch_bytes(url: str, timeout: int = 60) -> bytes:
    if is_ee_firms_url(url):
        raise RuntimeError("EE FIRMS is not the live gun")
    req = urllib.request.Request(url, headers={"User-Agent": "tmc-gate/0.1 (Coast Range TMC)"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def parse_csv(text: str, source: str = "noaa20") -> list[FirmsDetection]:
    rows: list[FirmsDetection] = []
    reader = csv.DictReader(io.StringIO(text))
    for raw in reader:
        try:
            lat = float(raw["latitude"])
            lon = float(raw["longitude"])
            scan = float(raw.get("scan") or 0.375)
            track = float(raw.get("track") or 0.375)
            frp = float(raw.get("frp") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        rows.append(
            FirmsDetection(
                latitude=lat,
                longitude=lon,
                acq_date=str(raw.get("acq_date") or ""),
                acq_time=str(raw.get("acq_time") or "").strip(),
                satellite=str(raw.get("satellite") or ""),
                confidence=str(raw.get("confidence") or "").strip().lower(),
                frp=frp,
                scan_km=scan if scan > 0 else 0.375,
                track_km=track if track > 0 else 0.375,
                daynight=str(raw.get("daynight") or ""),
                source=source,
            )
        )
    return rows


def load_csv_path(path: Path, source: str = "noaa20") -> list[FirmsDetection]:
    return parse_csv(path.read_text(encoding="utf-8"), source=source)


def in_d5_bbox(det: FirmsDetection) -> bool:
    lat_min, lat_max, lon_min, lon_max = D5_BBOX
    return lat_min <= det.latitude <= lat_max and lon_min <= det.longitude <= lon_max


def filter_d5(dets: list[FirmsDetection]) -> list[FirmsDetection]:
    """Clip national FIRMS CSV to the D5-shaped window before spatial join."""
    return [d for d in dets if in_d5_bbox(d)]


def native_pixel_polygon(det: FirmsDetection) -> Polygon:
    """VIIRS scan×track rectangle in WGS84. Native footprint, not 100-ft buffer.

    Probed [R6] KML (31 Aug 2026) is Point placemarks (~1.4 MB). The native
    geometry for ST_Intersects is the sensor pixel reconstructed from CSV
    `scan` and `track` (km). Do not substitute a 100-foot / 30-metre buffer.
    """
    if abs(det.scan_km * 1000.0 - _FT100_M) < 0.5 and abs(det.track_km * 1000.0 - _FT100_M) < 0.5:
        raise ValueError("refusing 100-ft buffer disguised as scan/track")
    dlat = (det.track_km / 2.0) / 110.574
    cos_lat = math.cos(math.radians(det.latitude))
    denom = 111.320 * cos_lat if abs(cos_lat) > 0.01 else 111.320
    dlon = (det.scan_km / 2.0) / denom
    return Polygon(
        [
            (det.longitude - dlon, det.latitude - dlat),
            (det.longitude + dlon, det.latitude - dlat),
            (det.longitude + dlon, det.latitude + dlat),
            (det.longitude - dlon, det.latitude + dlat),
            (det.longitude - dlon, det.latitude - dlat),
        ]
    )


def invented_100ft_buffer_m() -> None:
    """Intentionally absent. ST_DWithin only if Gemini quoted a numeric buffer from prose."""
    return None
