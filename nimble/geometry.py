"""Spherical polar stereographic math for the lunar poles.

Matches the ISIS / LROC RDR definition: sphere R = 1737.4 km, true scale at
the pole (k0 = 1).  South pole forward equations:

    rho = 2 R tan(pi/4 - |lat|/2)        (|lat| in radians, lat < 0)
    x   = rho * sin(lon - lon0)
    y   = rho * cos(lon - lon0)

Point scale factor (map metres per ground metre):  k = 2 / (1 + sin|lat|)
"""
import math

R_MOON = 1737400.0  # m, IAU/LROC reference sphere


def ll_to_xy_south(lat, lon, lon0=0.0, R=R_MOON):
    phi = math.radians(abs(lat))
    rho = 2 * R * math.tan(math.pi / 4 - phi / 2)
    d = math.radians(lon - lon0)
    return rho * math.sin(d), rho * math.cos(d)


def xy_to_ll_south(x, y, lon0=0.0, R=R_MOON):
    rho = math.hypot(x, y)
    phi = math.pi / 2 - 2 * math.atan(rho / (2 * R))
    lon = (lon0 + math.degrees(math.atan2(x, y))) % 360.0
    return -math.degrees(phi), lon


def scale_factor(lat):
    return 2.0 / (1.0 + math.sin(math.radians(abs(lat))))


def great_circle_m(lat1, lon1, lat2, lon2, R=R_MOON):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    a = math.sin((p2 - p1) / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def box_south(lat_c, lon_c, size_m, lon0=0.0):
    """Map-grid-aligned square box centred on (lat_c, lon_c). Returns dict."""
    xc, yc = ll_to_xy_south(lat_c, lon_c, lon0)
    h = size_m / 2
    corners_xy = [(xc - h, yc + h), (xc + h, yc + h), (xc + h, yc - h), (xc - h, yc - h)]
    return {
        "center_xy": (xc, yc),
        "xmin": xc - h, "xmax": xc + h, "ymin": yc - h, "ymax": yc + h,
        "corners_xy": corners_xy,
        "corners_ll": [xy_to_ll_south(x, y, lon0) for x, y in corners_xy],
    }


def latlon_bounds(b, lon0=0.0, n=60):
    """Dense-sample a box (from box_south) -> (minlat, maxlat, wlon, elon), lon in 0..360.
    Assumes the box does not contain the pole or straddle lon 0/360."""
    lats, lons = [], []
    for i in range(n + 1):
        for j in range(n + 1):
            x = b["xmin"] + (b["xmax"] - b["xmin"]) * i / n
            y = b["ymin"] + (b["ymax"] - b["ymin"]) * j / n
            la, lo = xy_to_ll_south(x, y, lon0)
            lats.append(la)
            lons.append(lo)
    return min(lats), max(lats), min(lons), max(lons)
