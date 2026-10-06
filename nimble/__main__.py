"""NIMBLE command line.

    python -m nimble extract --name ConnectingRidge --lat -89.46 --lon -137.08 --size-km 20

Pulls the 1 m/px LROC NAC South Pole controlled mosaic window centred on the
point, writes GeoTIFFs + preview + run manifest, and lists the NAC strips that
LROC used in the mosaic and that touch the box.
"""
import argparse
import csv
import datetime as dt
import json
import os
import sys

import numpy as np

from . import __version__
from .geometry import box_south, latlon_bounds, scale_factor
from .pds import browse_geotransform, fetch_text, fetch_window, parse_image_list, parse_label, rdr_url, window_for_box
from .ode import query_nac, intersect_box
from . import report
from .export import crs_south, preview_png, write_geotiffs

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POLE_DIR = "LROLRC_2001/DATA/BDR/NAC_POLE/NAC_POLE_SOUTH/"


def pick_south_tile(lat, lon):
    lon = lon % 360
    if lat <= -88.5:  # polar cap ring: four 90-degree quadrants
        q = int(lon // 90)
        return f"NAC_POLE_P892S{q * 900 + 450:04d}"
    raise SystemExit("v0.1 only supports the -88.5..-90 polar cap tiles; outer rings are on the roadmap")


def cmd_extract(a):
    run = os.path.join(ROOT, "runs", a.name)
    os.makedirs(run, exist_ok=True)
    log_f = open(os.path.join(run, "run.log"), "a", encoding="utf-8")

    def log(*m):
        s = " ".join(str(x) for x in m)
        print(s, flush=True)
        log_f.write(s + "\n")
        log_f.flush()

    log(f"=== NIMBLE {__version__}  {dt.datetime.now(dt.timezone.utc).isoformat()}")
    tile = a.tile or pick_south_tile(a.lat, a.lon)
    lbl_url = rdr_url(POLE_DIR + tile + ".xml")
    img_url = rdr_url(POLE_DIR + tile + ".IMG")
    log("tile", tile)
    lbl_txt = fetch_text(lbl_url)
    open(os.path.join(run, tile + ".xml"), "w", encoding="utf-8").write(lbl_txt)
    lab = parse_label(lbl_txt)
    log("label", json.dumps(lab))
    # Cross-check georeference against the LROC browse GeoTIFF (authoritative when present)
    try:
        gx, gy, grx, gry, gw, gh = browse_geotransform(
            POLE_DIR.replace("DATA/BDR", "EXTRAS/BROWSE") + tile + ".TIF")
        dx, dy = gx - lab["ulx"], gy - lab["uly"]
        log(f"browse GeoTIFF UL=({gx}, {gy}) res={grx} size={gw}x{gh}; label-derived "
            f"UL=({lab['ulx']}, {lab['uly']}); diff=({dx}, {dy}) m")
        if (gw, gh) != (lab["samples"], lab["lines"]) or abs(dx) > 0.01 or abs(dy) > 0.01:
            log("WARNING: label and browse GeoTIFF disagree; using browse GeoTIFF georeference")
        lab["ulx"], lab["uly"], lab["pixel_res_x"], lab["pixel_res_y"] = gx, gy, grx, gry
        lab["georef_check"] = {"browse_ul": [gx, gy], "diff_m": [dx, dy]}
    except Exception as ex:  # noqa: BLE001
        log("WARNING: could not read browse GeoTIFF georeference:", ex)

    size_m = a.size_km * 1000
    b = box_south(a.lat, a.lon, size_m, lon0=lab["lon0"])
    win = window_for_box(lab, b["xmin"], b["ymin"], b["xmax"], b["ymax"])
    row0, row1, col0, col1 = win
    # snap box to the pixel grid actually extracted
    xmin = lab["ulx"] + col0 * lab["pixel_res_x"]
    ymax = lab["uly"] - row0 * lab["pixel_res_y"]
    log(f"window rows {row0}:{row1} cols {col0}:{col1}  ({row1 - row0} x {col1 - col0} px)")

    npy = os.path.join(ROOT, "data", "cache", f"{a.name}_{tile}_{row0}_{row1}_{col0}_{col1}.npy")
    os.makedirs(os.path.dirname(npy), exist_ok=True)
    arr = fetch_window(img_url, lab, win, npy, block_rows=a.block_rows, log=log)
    if lab["scaling_factor"] != 1.0 or lab["value_offset"] != 0.0:
        log("NOTE: label has scaling; science GeoTIFF stores scaled values")

    # Source-strip bookkeeping --------------------------------------------------
    lst_txt = fetch_text(rdr_url(POLE_DIR + "NAC_POLE_SOUTH_IMAGES.TXT"))
    open(os.path.join(run, "NAC_POLE_SOUTH_IMAGES.TXT"), "w", encoding="utf-8").write(lst_txt)
    readme = fetch_text(rdr_url(POLE_DIR + "NAC_POLE_SOUTH_README.TXT"))
    open(os.path.join(run, "NAC_POLE_SOUTH_README.TXT"), "w", encoding="utf-8").write(readme)
    in_mosaic = {s[:-1] if s[-1] in "EC" else s for s in parse_image_list(lst_txt)}
    la0, la1, lo0, lo1 = latlon_bounds(b, lab["lon0"])
    prods = query_nac(la0 - 0.01, la1 + 0.01, lo0 - 0.5, lo1 + 0.5)
    strips = intersect_box(prods, xmin, ymax - (row1 - row0) * lab["pixel_res_y"],
                           xmin + (col1 - col0) * lab["pixel_res_x"], ymax)
    for s in strips:
        s["in_mosaic"] = s["Product_name"][:-1] in in_mosaic
    strips.sort(key=lambda s: (not s["in_mosaic"], -s["box_cover_frac"]))
    fields = ["Product_name", "in_mosaic", "box_cover_frac", "Observation_time", "Incidence_angle",
              "Emission_angle", "Phase_angle", "Map_resolution", "Solar_longitude", "External_url"]
    with open(os.path.join(run, "STRIPS_IN_BOX.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(strips)
    used = [s for s in strips if s["in_mosaic"]]
    log(f"NAC strips touching box: {len(strips)}; of those listed in mosaic: {len(used)}")

    # Export ------------------------------------------------------------------
    tags = {"NIMBLE_VERSION": __version__, "SOURCE_PRODUCT": tile,
            "CENTER_LAT": a.lat, "CENTER_LON_E": a.lon % 360, "SIZE_M": size_m,
            "PIXEL_WINDOW": f"rows {row0}:{row1} cols {col0}:{col1}"}
    base = os.path.join(run, f"{a.name}_{int(a.size_km)}km_1mpp")
    lo, hi = write_geotiffs(arr, xmin, ymax, lab["pixel_res_x"],
                            crs_south(lab["lon0"], lab["radius_a"]),
                            base + "_IoF_float32.tif", base + "_8bit.tif", tags)
    north = preview_png(base + "_8bit.tif", base + "_preview.png", b["center_xy"],
                        f"{a.name}  {a.lat}, {a.lon}  {a.size_km:g} km  LROC NAC 1 m/px")
    m = np.asarray(arr[::50, ::50])
    valid = float(np.mean(np.isfinite(m) & (m > -1e30) & (m != 0)))
    man = {
        "nimble_version": __version__, "utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "request": vars(a), "tile": tile, "label_url": lbl_url, "image_url": img_url,
        "label": lab, "pixel_window": win, "box_map_m": {"xmin": xmin, "ymax": ymax,
        "xmax": xmin + (col1 - col0) * lab["pixel_res_x"],
        "ymin": ymax - (row1 - row0) * lab["pixel_res_y"]},
        "center_xy_m": b["center_xy"], "corners_latlon": b["corners_ll"],
        "scale_factor_center": scale_factor(a.lat),
        "north_azimuth_deg_cw_from_image_up": north, "stretch_8bit": [lo, hi],
        "valid_pixel_fraction": valid, "strips_touching_box": len(strips),
        "strips_in_mosaic_touching_box": len(used),
    }
    json.dump(man, open(os.path.join(run, "manifest.json"), "w"), indent=1)
    log(json.dumps(man, indent=1, default=str))
    log("wrote", report.write(run))


def main(argv=None):
    p = argparse.ArgumentParser(prog="nimble")
    sp = p.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("extract", help="cut a square patch out of the LROC NAC polar mosaic")
    e.add_argument("--name", required=True)
    e.add_argument("--lat", type=float, required=True)
    e.add_argument("--lon", type=float, required=True, help="degrees, east-positive (-137.08 ok)")
    e.add_argument("--size-km", type=float, default=20)
    e.add_argument("--tile", help="override source product id")
    e.add_argument("--block-rows", type=int, default=512)
    r = sp.add_parser("report", help="regenerate METHODS_AND_MATH.txt for a run")
    r.add_argument("--name", required=True)
    a = p.parse_args(argv)
    if a.cmd == "extract":
        cmd_extract(a)
    elif a.cmd == "report":
        print(report.write(os.path.join(ROOT, "runs", a.name)))


if __name__ == "__main__":
    sys.exit(main())
