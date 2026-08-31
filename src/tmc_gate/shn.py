"""Public Caltrans SHN FeatureServer. No key. Named objects for the join."""

from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from shapely.geometry import shape

from tmc_gate.constants import D5_COUNTIES, SHN_FEATURESERVER
from tmc_gate.models import ShnSegment


def query_url(where: str) -> str:
    q = urlencode(
        {
            "where": where,
            "outFields": "County,Route,bPM,ePM",
            "f": "geojson",
            "outSR": "4326",
            "resultRecordCount": "2000",
        }
    )
    return f"{SHN_FEATURESERVER}?{q}"


def fetch_geojson(where: str, timeout: int = 60) -> dict:
    req = Request(query_url(where), headers={"User-Agent": "tmc-gate/0.1 (Coast Range TMC)"})
    with urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def parse_geojson(doc: dict) -> list[ShnSegment]:
    out: list[ShnSegment] = []
    for feat in doc.get("features") or []:
        props = feat.get("properties") or {}
        geom = feat.get("geometry")
        if not geom:
            continue
        county = str(props.get("County") or "").upper()
        try:
            route = int(props.get("Route"))
            bpm = float(props.get("bPM"))
            epm = float(props.get("ePM"))
        except (TypeError, ValueError):
            continue
        g = shape(geom)
        out.append(
            ShnSegment(
                county=county,
                route=route,
                bpm=bpm,
                epm=epm,
                wkt=g.wkt,
                geometry=g,
                d5=county in D5_COUNTIES,
            )
        )
    return out


def load_geojson_path(path: Path) -> list[ShnSegment]:
    return parse_geojson(json.loads(path.read_text(encoding="utf-8")))


def d5_route1(segments: list[ShnSegment]) -> list[ShnSegment]:
    return [s for s in segments if s.d5 and s.route == 1]


def unique_spans(segments: list[ShnSegment]) -> list[ShnSegment]:
    """SHN often duplicates both directions. Keep one geometry per span."""
    seen: dict[tuple, ShnSegment] = {}
    for s in segments:
        key = (s.county, s.route, round(s.bpm, 3), round(s.epm, 3))
        if key not in seen:
            seen[key] = s
    return list(seen.values())
