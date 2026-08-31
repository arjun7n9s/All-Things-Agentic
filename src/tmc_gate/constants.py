"""Named constants. No invented 100-ft / 30-m buffer lives here."""

from __future__ import annotations

FIXTURE_TMC = "Coast Range TMC"
TZ = "America/Los_Angeles"
D5_OPEN = "06:00"
D5_CLOSE = "18:00"

# D5-shaped clip. SHN County field uses MON (probed).
D5_COUNTIES = frozenset({"MON", "SLO", "SB", "SCR", "SBT"})

# Live gun is FIRMS CSV/KML. Not EE ImageCollection("FIRMS").
FIRMS_CSV = {
    "noaa20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv",
    "snpp": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/csv/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv",
    "noaa21": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/csv/J2_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv",
    "modis": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/csv/MODIS_C6_1_USA_contiguous_and_Hawaii_24h.csv",
}
FIRMS_KML = {
    "noaa20": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/kml/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.kml",
    "snpp": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/suomi-npp-viirs-c2/kml/SUOMI_VIIRS_C2_USA_contiguous_and_Hawaii_24h.kml",
    "noaa21": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-21-viirs-c2/kml/J2_VIIRS_C2_USA_contiguous_and_Hawaii_24h.kml",
    "modis": "https://firms.modaps.eosdis.nasa.gov/data/active_fire/modis-c6.1/kml/MODIS_C6_1_USA_contiguous_and_Hawaii_24h.kml",
}

SHN_FEATURESERVER = (
    "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/"
    "CHhighway/SHN_Lines/FeatureServer/0/query"
)
TOM_PDF_URL = (
    "https://dot.ca.gov/-/media/dot-media/programs/traffic-operations/"
    "documents/trafficops/202602-tom-ch-110-transportation-mgmt-centers-a11y.pdf"
)

NASADEM_ID = "NASA/NASADEM_HGT/001"
EE_FIRMS_COLLECTION = "FIRMS"  # 1-day lag. Forbidden as live gun.

VIIRS_OK_CONF = frozenset({"nominal", "high"})
ADK_CALL_BOUND = 12

# Film target. Real SHN row (probed): MON Route 1 bPM 33.835 ePM 71.169 contains PM 47.
FILM_ROUTE = "CA-1"
FILM_PM = "PM47"
FILM_PM_NUMBER = 47.0

UNREACHABLE_PATHS = (
    "/publish",
    "/traveler-info",
    "/cad",
    "/hard-closure",
    "/cones",
    "/blast",
    "/scale",
    "/rock",
    "/facility-reopen",
    "/fema",
    "/caloes",
    "/declaration",
    "/sigalert",
    "/drone",
    "/engines",
    "/dispatch",
    "/email",
    "/mailto",
    "/cloud-run",
    "/run.app",
    "/psps",
    "/scada-reclose",
)

FORBIDDEN_TOOL_NAMES = frozenset(
    {
        "publish_traveler_info",
        "call_cad",
        "place_cones",
        "blast_rock",
        "reopen_facility",
        "declare_emergency",
        "issue_sigalert",
        "psps",
        "send_email",
        "dispatch_engines",
    }
)
