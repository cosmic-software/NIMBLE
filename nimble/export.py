"""Write science + viewing GeoTIFFs and an annotated preview PNG."""
import math

import numpy as np
import rasterio
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from PIL import Image, ImageDraw, ImageFont

PROJ_SOUTH = "+proj=stere +lat_0=-90 +lon_0={lon0} +k=1 +x_0=0 +y_0=0 +R={R} +units=m +no_defs"


def crs_south(lon0=0.0, R=1737400.0):
    if lon0 == 0.0 and R == 1737400.0:
        try:
            return CRS.from_string("IAU_2015:30135")  # Moon south polar stereographic
        except Exception:
            pass
    return CRS.from_proj4(PROJ_SOUTH.format(lon0=lon0, R=R))


def valid_mask(a):
    return np.isfinite(a) & (a > -1e30) & (a != 0)


def robust_stretch(a, lo_pct=0.5, hi_pct=99.5, sample=4_000_000):
    flat = a.reshape(-1)
    idx = np.random.default_rng(0).integers(0, flat.size, min(sample, flat.size))
    s = flat[idx]
    s = s[valid_mask(s)]
    return (float(np.percentile(s, lo_pct)), float(np.percentile(s, hi_pct))) if s.size else (0, 1)


def write_geotiffs(arr, xmin, ymax, res, crs, sci_path, view_path, tags=None, chunk=2048):
    h, w = arr.shape
    tr = from_origin(xmin, ymax, res, res)
    common = dict(driver="GTiff", height=h, width=w, count=1, crs=crs, transform=tr,
                  tiled=True, blockxsize=512, blockysize=512, BIGTIFF="YES")
    lo, hi = robust_stretch(arr)
    with rasterio.open(sci_path, "w", dtype="float32", nodata=-3.4028226550889045e38,
                       compress="deflate", predictor=3, zlevel=6, **common) as sci, \
         rasterio.open(view_path, "w", dtype="uint8", nodata=0,
                       compress="deflate", predictor=2, **common) as vw:
        for r0 in range(0, h, chunk):
            r1 = min(r0 + chunk, h)
            blk = np.asarray(arr[r0:r1], dtype="float32")
            m = valid_mask(blk)
            sblk = np.where(m, blk, -3.4028226550889045e38).astype("float32")
            win = rasterio.windows.Window(0, r0, w, r1 - r0)
            sci.write(sblk, 1, window=win)
            v = np.clip((np.where(m, blk, lo) - lo) / (hi - lo) * 254 + 1, 1, 255)
            vw.write(np.where(m, v, 0).astype("uint8"), 1, window=win)
        for ds in (sci, vw):
            ds.update_tags(**(tags or {}))
            ds.update_tags(STRETCH_LO=lo, STRETCH_HI=hi)
        sci.build_overviews([2, 4, 8, 16, 32], Resampling.average)
        vw.build_overviews([2, 4, 8, 16, 32], Resampling.average)
    return lo, hi


def preview_png(view_path, png_path, center_xy, title, size=4000):
    with rasterio.open(view_path) as ds:
        f = max(1, ds.width // size)
        img = ds.read(1, out_shape=(ds.height // f, ds.width // f), resampling=Resampling.average)
        res = ds.res[0] * ds.width / img.shape[1]
    im = Image.fromarray(img).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype("arial.ttf", max(18, im.width // 80))
    except OSError:
        font = ImageFont.load_default()
    W, H = im.size
    pad = W // 40
    # scale bar: 2 km
    L = int(2000 / res)
    y = H - pad
    d.rectangle([pad, y - 12, pad + L, y], fill=(255, 255, 255))
    d.rectangle([pad + L // 2, y - 12, pad + L, y], fill=(0, 0, 0), outline=(255, 255, 255))
    d.text((pad, y - 50), "2 km", fill=(255, 255, 0), font=font)
    # north arrow: north = away from the pole = +radial direction in map coords
    x, yy = center_xy
    ang = math.atan2(x, yy)  # radial direction measured clockwise from map +y (image up)
    cx, cy, L2 = W - 3 * pad, 3 * pad, 2 * pad
    ex, ey = cx + L2 * math.sin(ang), cy - L2 * math.cos(ang)
    d.line([cx, cy, ex, ey], fill=(255, 255, 0), width=6)
    d.ellipse([ex - 10, ey - 10, ex + 10, ey + 10], fill=(255, 255, 0))
    d.text((ex + 12, ey), "N", fill=(255, 255, 0), font=font)
    d.text((pad, pad), title, fill=(255, 255, 0), font=font)
    im.save(png_path, optimize=True)
    return math.degrees(ang) % 360.0
