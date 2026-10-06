"""Query WUSTL ODE REST for LROC NAC strip footprints (south polar stereographic)."""
import json, time, requests
from shapely import wkt
from shapely.geometry import box as sbox

ODE = "https://oderest.rsl.wustl.edu/live2/"
KEEP = ["pdsid", "Product_name", "Observation_time", "Incidence_angle", "Emission_angle",
        "Phase_angle", "Map_resolution", "Solar_longitude", "Center_latitude",
        "Center_longitude", "Comment", "External_url", "LabelURL"]


def query_nac(minlat, maxlat, wlon, elon, pt="CDRNAC4", page=100, pause=0.5):
    out, offset = [], 0
    while True:
        r = requests.get(ODE, params=dict(query="product", target="moon", ihid="LRO", iid="LROC",
                                          pt=pt, results="m", output="JSON", minlat=minlat,
                                          maxlat=maxlat, westernlon=wlon, easternlon=elon,
                                          limit=page, offset=offset), timeout=120)
        r.raise_for_status()
        prods = r.json()["ODEResults"].get("Products", {})
        prods = prods.get("Product", []) if isinstance(prods, dict) else []
        prods = prods if isinstance(prods, list) else [prods]
        out += prods
        if len(prods) < page:
            return out
        offset += page
        time.sleep(pause)


def intersect_box(products, xmin, ymin, xmax, ymax):
    """Return records with fraction of the map box covered by each strip footprint."""
    B = sbox(xmin, ymin, xmax, ymax)
    rows = []
    for p in products:
        g = p.get("Footprint_SP_geometry")
        if not g:
            continue
        geom = wkt.loads(g)
        if not geom.is_valid:
            geom = geom.buffer(0)
        inter = geom.intersection(B)
        if inter.is_empty:
            continue
        rec = {k: p.get(k) for k in KEEP}
        rec["Product_name"] = (rec["Product_name"] or "").replace(".IMG", "")
        rec["box_cover_frac"] = round(inter.area / B.area, 4)
        rec["footprint_wkt_sp"] = g
        rows.append(rec)
    return rows
