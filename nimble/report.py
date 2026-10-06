"""Generate METHODS_AND_MATH.txt for a run folder from its manifest + strip table."""
import csv
import json
import math
import os

from .geometry import R_MOON, great_circle_m, scale_factor, xy_to_ll_south

TEMPLATE = """\
NIMBLE {ver} — METHODS, MATH AND SOURCE STRIPS
Run: {name}        Generated (UTC): {utc}
==========================================================================================

1. WHAT THIS PRODUCT IS
------------------------------------------------------------------------------------------
A {size_km:g} km x {size_km:g} km image patch at 1.00 m/pixel ({w} x {h} pixels = {mp:.0f} megapixels)
centred on {lat}, {lon_in} ({lon_e:.2f} E), cut directly out of the LROC South Pole NAC
Mosaic (PDS product {tile}, LRO-L-LROC-5-RDR-V1.0). The LROC team built that mosaic from
individual Narrow Angle Camera frames that were radiometrically calibrated, controlled, and
orthorectified, then map-projected at 1 m/px (see BIBLIOGRAPHY [D1], [4]).

NIMBLE did NOT resample, reproject, blend or filter any pixel. The science GeoTIFF holds the exact
float32 I/F values of the source product for the pixel window below. The 8-bit GeoTIFF/PNG is a
linear display stretch only (I/F {lo:.5f} -> 1, {hi:.5f} -> 255; 0 = no data). Measure on the float32 file.

Files:
  {base}_IoF_float32.tif   science raster (I/F, float32, nodata = -3.4028226550889045e38)
  {base}_8bit.tif          display raster (uint8, same grid)
  {base}_preview.png       ~4k overview with 2 km scale bar and north arrow
  STRIPS_IN_BOX.csv        every LROC NAC frame whose footprint touches the box (flag: in_mosaic)
  NAC_POLE_SOUTH_IMAGES.TXT / _README.TXT / {tile}.xml   LROC source documentation
  manifest.json, run.log   full machine-readable provenance

2. COORDINATE REFERENCE SYSTEM
------------------------------------------------------------------------------------------
Body:            Moon, reference sphere R = {R:.1f} m (IAU 2015 mean radius)  [8]
Projection:      Polar stereographic, south pole origin, central meridian lon0 = {lon0:g} deg,
                 true scale at the pole (k0 = 1). CRS = IAU_2015:30135 (PROJ:
                 +proj=stere +lat_0=-90 +lon_0={lon0:g} +k=1 +x_0=0 +y_0=0 +R={R:.0f} +units=m)
Longitudes:      east-positive, 0-360 (input -137.08 deg == 222.92 deg E)

Forward equations (Snyder 1987, spherical polar stereographic, south aspect)  [7]:
    rho = 2 R tan(pi/4 - |phi|/2)
    x   = rho sin(lambda - lambda0)
    y   = rho cos(lambda - lambda0)
Inverse:
    rho    = sqrt(x^2 + y^2)
    |phi|  = pi/2 - 2 atan(rho / 2R)          phi = -|phi|
    lambda = lambda0 + atan2(x, y)
Point scale factor (map length / ground length):
    k = 2 / (1 + sin|phi|)

3. THE NUMBERS FOR THIS PATCH
------------------------------------------------------------------------------------------
Centre:          phi = {lat} deg, lambda = {lon_e:.4f} deg E
  rho            = 2 x {R:.0f} x tan(45 deg - {abslat}/2 deg) = {rho:.3f} m from the pole
  (x, y)         = ({cx:.3f}, {cy:.3f}) m
Box (map-grid aligned, half-width {half:.0f} m, snapped to source pixel edges):
  x: {xmin:.1f} .. {xmax:.1f} m      y: {ymin:.1f} .. {ymax:.1f} m
Corner lat/lon (UL, UR, LR, LL):
{corners}
Latitude span:   {latmin:.4f} .. {latmax:.4f} deg   (the box does NOT contain the pole)

Source pixel window in {tile}  ({lines} lines x {samples} samples, upper-left
  corner x = {ulx:.1f} m, y = {uly:.1f} m, pixel = {px:.4f} m):
    row = (y_UL - y) / pixel  ->  rows {row0}..{row1}
    col = (x - x_UL) / pixel  ->  cols {col0}..{col1}

Scale distortion (why 1 map metre = 1 ground metre here):
  k(centre) = 2/(1+sin {abslat}) = {k_c:.8f}  -> {ppm_c:.1f} ppm
  k(range)  = {k_lo:.8f} .. {k_hi:.8f} over the box
  => a 20 m boulder measured in map units is long by at most {err20:.5f} m (negligible);
     a 20 km baseline is long by at most {err20k:.2f} m.
  Check: the map edge UL->UR measured as a great-circle arc on the sphere = {edge:.2f} m.
  Independent check: NIMBLE projection math vs PROJ (IAU_2015:30135) agrees to < 1e-6 m
  (tests/test_geometry.py).

Orientation:
  Image "up" is map +y (toward 0 deg E from the pole). Lunar north at the patch centre
  points {north:.2f} deg clockwise from image-up (the arrow on the preview). Because every
  meridian converges on the pole, north rotates across the patch: from {north_lo:.1f} deg to
  {north_hi:.1f} deg between the box corners. Do not assume a single "north" for azimuths;
  use the map grid or compute per point: azimuth_north = atan2(x, y).

Sun geometry (context for shadows):
  At |phi| = {abslat} deg the sun's elevation never exceeds about 1.54 deg (max solar
  declination) + {colat:.2f} deg (colatitude) = {maxel:.2f} deg. A 1 m tall boulder therefore
  casts a shadow >= 1/tan({maxel:.2f} deg) = {shadow:.0f} m long. Shadow length is a
  powerful height measure here but needs per-image sun elevation (see STRIPS_IN_BOX.csv
  incidence angles; elevation = 90 - incidence on flat ground).

Coverage: {valid:.1%} of sampled pixels hold valid data ({nodata:.1%} no-data, i.e. permanent shadow
or gaps that the LROC mosaic left empty).

4. ACCURACY STATEMENT
------------------------------------------------------------------------------------------
* Pixel scale 1.00 m. Rocks smaller than about 2-3 m are not resolvable by outline. Long polar
  shadows reveal smaller rocks, but their size must come from shadow length + sun elevation.
* Relative geometry inside a single source frame is excellent (sub-pixel). Across mosaic seams,
  features can be offset by a few pixels: measure objects away from seams.
* Absolute position is the LROC mosaic's control accuracy (see NAC_POLE_SOUTH_README.TXT);
  this affects where the patch is, not how big a rock is.
* Map-projection scale error: < {ppm_max:.0f} ppm (computed above).

5. SOURCE NAC STRIPS
------------------------------------------------------------------------------------------
ODE (WUSTL) footprint search: {n_all} LROC NAC CDR frames have footprints touching this box.
{n_used} of them are in the LROC NAC_POLE_SOUTH mosaic image list, i.e. they are the strips
that can contribute pixels to this patch. Listed below (all {n_all} are in STRIPS_IN_BOX.csv).
Columns: frame id | UTC | % of box covered by footprint | incidence | emission | phase | native m/px

{strip_table}
"""


def write(run_dir):
    m = json.load(open(os.path.join(run_dir, "manifest.json")))
    rows = list(csv.DictReader(open(os.path.join(run_dir, "STRIPS_IN_BOX.csv"))))
    lab, req, bx = m["label"], m["request"], m["box_map_m"]
    lat, lon_e = req["lat"], req["lon"] % 360
    R, lon0 = lab["radius_a"], lab["lon0"]
    cx, cy = m["center_xy_m"]
    rho = math.hypot(cx, cy)
    row0, row1, col0, col1 = m["pixel_window"]
    corners_xy = [(bx["xmin"], bx["ymax"]), (bx["xmax"], bx["ymax"]),
                  (bx["xmax"], bx["ymin"]), (bx["xmin"], bx["ymin"])]
    cll = [xy_to_ll_south(x, y, lon0) for x, y in corners_xy]
    lats = [c[0] for c in cll]
    # k grows with distance from the pole: min at the box point nearest the pole
    # ((0,0) clamped into the box), max at the farthest corner.
    nx = min(max(0.0, bx["xmin"]), bx["xmax"])
    ny = min(max(0.0, bx["ymin"]), bx["ymax"])
    rho_near = math.hypot(nx, ny)
    rho_far = max(math.hypot(x, y) for x, y in corners_xy)
    lat_of = lambda r: -(90 - math.degrees(2 * math.atan(r / (2 * R))))
    k_lo, k_hi = scale_factor(lat_of(rho_near)), scale_factor(lat_of(rho_far))
    lats.append(lat_of(rho_near))
    norths = [math.degrees(math.atan2(x, y)) % 360.0 for x, y in corners_xy]
    colat = 90 - abs(lat)
    maxel = 1.54 + colat
    used = [r for r in rows if r["in_mosaic"] == "True"]
    tbl = "\n".join(
        f"  {r['Product_name']:<14} {r['Observation_time'][:19]:<20} {float(r['box_cover_frac']) * 100:5.1f}%  "
        f"i={float(r['Incidence_angle'] or 'nan'):6.2f}  e={float(r['Emission_angle'] or 'nan'):5.2f}  "
        f"g={float(r['Phase_angle'] or 'nan'):6.2f}  {float(r['Map_resolution'] or 'nan'):5.2f}"
        for r in used) or "  (none matched — see STRIPS_IN_BOX.csv)"
    base = f"{req['name']}_{int(req['size_km'])}km_1mpp"
    edge = great_circle_m(*cll[0], *cll[1])
    txt = TEMPLATE.format(
        ver=m["nimble_version"], name=req["name"], utc=m["utc"], size_km=req["size_km"],
        w=col1 - col0, h=row1 - row0, mp=(col1 - col0) * (row1 - row0) / 1e6, lat=lat,
        lon_in=req["lon"], lon_e=lon_e, tile=m["tile"], lo=m["stretch_8bit"][0],
        hi=m["stretch_8bit"][1], base=base, R=R, lon0=lon0, abslat=abs(lat), rho=rho, cx=cx, cy=cy,
        half=req["size_km"] * 500, xmin=bx["xmin"], xmax=bx["xmax"], ymin=bx["ymin"], ymax=bx["ymax"],
        corners="\n".join(f"  {n}: {la:.5f}, {lo:.4f} E" for n, (la, lo) in zip(["UL", "UR", "LR", "LL"], cll)),
        latmin=min(lats), latmax=max(lats), lines=lab["lines"], samples=lab["samples"],
        ulx=lab["ulx"], uly=lab["uly"], px=lab["pixel_res_x"], row0=row0, row1=row1, col0=col0, col1=col1,
        k_c=scale_factor(lat), ppm_c=(scale_factor(lat) - 1) * 1e6, k_lo=k_lo, k_hi=k_hi,
        err20=20 * (k_hi - 1), err20k=20000 * (k_hi - 1), edge=edge,
        north=m["north_azimuth_deg_cw_from_image_up"], north_lo=min(norths), north_hi=max(norths),
        colat=colat, maxel=maxel, shadow=1 / math.tan(math.radians(maxel)),
        valid=m["valid_pixel_fraction"], nodata=1 - m["valid_pixel_fraction"],
        ppm_max=(k_hi - 1) * 1e6 + 1, n_all=len(rows), n_used=len(used), strip_table=tbl)
    path = os.path.join(run_dir, "METHODS_AND_MATH.txt")
    open(path, "w", encoding="utf-8").write(txt)
    return path
