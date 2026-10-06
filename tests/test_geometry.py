"""Cross-check NIMBLE polar stereographic math against PROJ (IAU_2015:30135)."""
import math
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pyproj import CRS, Transformer
from nimble.geometry import ll_to_xy_south, xy_to_ll_south, scale_factor, box_south, great_circle_m

PTS = [(-89.46, -137.08), (-89.0, 183), (-89.9, 265), (-88.5, 225), (-85, 10), (-87.3, 359.9)]


def test_against_proj():
    t = Transformer.from_crs(CRS.from_proj4("+proj=longlat +R=1737400 +no_defs"),
                             CRS.from_user_input("IAU_2015:30135"), always_xy=True)
    worst = 0
    for lat, lon in PTS:
        x1, y1 = ll_to_xy_south(lat, lon)
        x2, y2 = t.transform(lon, lat)
        worst = max(worst, math.hypot(x1 - x2, y1 - y2))
    assert worst < 1e-6, worst
    return worst


def test_round_trip():
    for lat, lon in PTS:
        la, lo = xy_to_ll_south(*ll_to_xy_south(lat, lon))
        d = abs(lo - lon) % 360
        assert abs(la - lat) < 1e-10 and min(d, 360 - d) < 1e-9


def test_scale_and_edges():
    assert abs(scale_factor(-89.46) - 1.0000222) < 1e-7
    b = box_south(-89.46, -137.08, 20000)
    (la1, lo1), (la2, lo2) = b["corners_ll"][0], b["corners_ll"][1]
    edge = great_circle_m(la1, lo1, la2, lo2)
    assert abs(edge - 20000) < 2.0, edge  # map edge vs. ground: < 2 m over 20 km
    return edge


if __name__ == "__main__":
    print("max |NIMBLE - PROJ| (m):", test_against_proj())
    test_round_trip(); print("round trip ok")
    print("20 km map edge measured on sphere (m):", test_scale_and_edges())
