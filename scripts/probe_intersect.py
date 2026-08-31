"""How many Frozen-A pixels actually ST_Intersect SHN with native VIIRS footprints?"""

from pathlib import Path

from tmc_gate.firms import load_csv_path, native_pixel_polygon
from tmc_gate.shn import load_geojson_path, unique_spans
from tmc_gate.wake import frozen_a_filter

ROOT = Path(__file__).resolve().parents[1]
dets = [d for d in load_csv_path(ROOT / "fixtures/firms/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv") if frozen_a_filter(d)]
segs = unique_spans(load_geojson_path(ROOT / "fixtures/shn/mon_ca1.geojson"))
hits = 0
best = None
for d in dets:
    fp = native_pixel_polygon(d)
    dist = min(fp.distance(s.geometry) for s in segs)
    if best is None or dist < best[0]:
        best = (dist, d.latitude, d.longitude, d.confidence)
    if any(fp.intersects(s.geometry) for s in segs):
        hits += 1
print("frozen_a n", len(dets), "intersects", hits, "min_deg", best)
# all 0926 in corridor
from tmc_gate.firms import load_csv_path as load
alld = load(ROOT / "fixtures/firms/J1_VIIRS_C2_USA_contiguous_and_Hawaii_24h.csv")
corr = [d for d in alld if d.acq_date=="2026-08-30" and d.acq_time.zfill(4)=="0926" and 35.80<=d.latitude<=36.40 and -121.90<=d.longitude<=-121.35]
ih=0
mb=None
for d in corr:
    fp = native_pixel_polygon(d)
    dist = min(fp.distance(s.geometry) for s in segs)
    if mb is None or dist < mb[0]:
        mb = (dist, d.latitude, d.longitude)
    if any(fp.intersects(s.geometry) for s in segs):
        ih += 1
print("corridor 0926 n", len(corr), "intersects", ih, "min_deg", mb)
# metres approx
if mb:
    print("min metres ~", mb[0]*111000)
