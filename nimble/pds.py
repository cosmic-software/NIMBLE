"""PDS4 label parsing + windowed HTTP range extraction for LROC map-projected RDRs.

Only the rows needed for a window are fetched, in large contiguous blocks
(few requests -> friendly to the PDS CloudFront rate limiter), then cropped to
the column range.  Progress is checkpointed so an interrupted pull resumes.
"""
import json
import os
import re
import time
import xml.etree.ElementTree as ET

import numpy as np
import requests

PDS_LROC = "https://pds.lroc.im-ldi.com/data/"
PDS_CLOUD = ("https://pds.mcp.nasa.gov/data/store/img/lunar_reconnaissance_orbiter/pds4/lroc/"
             "lro-l-lroc-5-rdr/")

DTYPES = {"IEEE754LSBSingle": "<f4", "IEEE754MSBSingle": ">f4", "SignedLSB2": "<i2",
          "SignedMSB2": ">i2", "UnsignedByte": "u1", "UnsignedLSB2": "<u2"}


def rdr_url(relpath):
    """relpath like 'LROLRC_2001/DATA/BDR/NAC_POLE/NAC_POLE_SOUTH/NAC_POLE_P892S2250.IMG'"""
    return PDS_CLOUD + relpath


def _strip_ns(root):
    for el in root.iter():
        if "}" in el.tag:
            el.tag = el.tag.split("}", 1)[1]
    return root


def _f(root, tag):
    el = root.find(f".//{tag}")
    return None if el is None else el.text.strip()


def parse_label(xml_text):
    """Extract array layout + map projection from a PDS4 LROC RDR label."""
    root = _strip_ns(ET.fromstring(xml_text))
    arr = root.find(".//Array_2D_Image")
    if arr is None:
        arr = root.find(".//Array_3D_Image")
    axes = {a.find("axis_name").text: int(a.find("elements").text)
            for a in arr.findall("Axis_Array")}
    elem = arr.find("Element_Array")
    lab = {
        "offset": int(arr.find("offset").text),
        "lines": axes.get("Line"),
        "samples": axes.get("Sample"),
        "dtype": DTYPES[elem.find("data_type").text],
        "scaling_factor": float(_f(elem, "scaling_factor") or 1.0),
        "value_offset": float(_f(elem, "value_offset") or 0.0),
        "missing_constant": _f(root, "missing_constant"),
        "null_constant": _f(root, "null_constant"),
        "low_repr_saturation": _f(root, "low_representation_saturation"),
        # Cartography (PDS4 cart dictionary)
        "projection": _f(root, "map_projection_name"),
        "lon0": float(_f(root, "longitude_of_central_meridian") or 0.0),
        "lat0": float(_f(root, "latitude_of_projection_origin") or -90.0),
        "scale_factor_k0": _f(root, "scale_factor_at_projection_origin"),
        # pixel_resolution_* in these labels is deg/pixel; the metric size is pixel_scale_*
        "pixel_res_x": float(_f(root, "pixel_scale_x")),
        "pixel_res_y": float(_f(root, "pixel_scale_y")),
        # LROC polar labels store the ISIS projection offsets (pixel-centre position of the
        # pole) under upperleft_corner_*, sign-flipped. Verified against the browse GeoTIFF
        # for NAC_POLE_P892S2250: offsets (45487.5, -0.5) -> true UL edge (-45488, 0) m.
        "label_corner_raw": (float(_f(root, "upperleft_corner_x")),
                             float(_f(root, "upperleft_corner_y"))),
        "radius_a": float(_f(root, "a_axis_radius") or 1737400.0),
    }
    px = lab["pixel_res_x"]
    lab["ulx"] = -lab["label_corner_raw"][0] * px - 0.5 * px
    lab["uly"] = -lab["label_corner_raw"][1] * px - 0.5 * px
    # PDS4 cart radii are often expressed in km
    if lab["radius_a"] < 10000:
        lab["radius_a"] *= 1000.0
    return lab


def window_for_box(lab, xmin, ymin, xmax, ymax):
    """Map-metre box -> integer (row0, row1, col0, col1) pixel window, half-open."""
    px, py = lab["pixel_res_x"], lab["pixel_res_y"]
    col0 = int(round((xmin - lab["ulx"]) / px))
    col1 = int(round((xmax - lab["ulx"]) / px))
    row0 = int(round((lab["uly"] - ymax) / py))
    row1 = int(round((lab["uly"] - ymin) / py))
    if col0 < 0 or row0 < 0 or col1 > lab["samples"] or row1 > lab["lines"]:
        raise ValueError(f"box falls outside product: rows {row0}:{row1} cols {col0}:{col1} "
                         f"vs {lab['lines']}x{lab['samples']}")
    return row0, row1, col0, col1


def fetch_window(url, lab, win, out_npy, block_rows=512, pause=2.0, session=None, log=print):
    """Pull rows row0:row1 in contiguous blocks, crop to cols, write into a .npy file.

    Each HTTP block is streamed into one reused buffer and the cropped rows are written
    with plain seek/write (no writable memmap), keeping memory flat at ~1 block.
    Returns a read-only memmap of the result.
    """
    row0, row1, col0, col1 = win
    nrow, ncol = row1 - row0, col1 - col0
    dt = np.dtype(lab["dtype"])
    odt = dt.newbyteorder("=")
    rowbytes = lab["samples"] * dt.itemsize
    ckpt = out_npy + ".done.json"
    done = set(json.load(open(ckpt))) if os.path.exists(ckpt) else set()
    if not os.path.exists(out_npy):
        m = np.lib.format.open_memmap(out_npy, mode="w+", dtype=odt, shape=(nrow, ncol))
        del m
    with open(out_npy, "rb") as f:
        np.lib.format.read_magic(f)
        np.lib.format.read_array_header_1_0(f)
        hdr = f.tell()
    buf = bytearray(block_rows * rowbytes)
    s = session or requests.Session()
    t0 = time.time()
    nbytes = 0
    with open(out_npy, "r+b") as fout:
        for b0 in range(row0, row1, block_rows):
            if b0 in done:
                continue
            b1 = min(b0 + block_rows, row1)
            start = lab["offset"] + b0 * rowbytes
            want = (b1 - b0) * rowbytes
            for attempt in range(8):
                try:
                    r = s.get(url, headers={"Range": f"bytes={start}-{start + want - 1}"},
                              timeout=600, stream=True)
                    if r.status_code == 206:
                        mv, got = memoryview(buf), 0
                        for chunk in r.iter_content(1 << 20):
                            mv[got:got + len(chunk)] = chunk
                            got += len(chunk)
                        if got == want:
                            break
                        log(f"  short read {got}/{want} on rows {b0}:{b1}; retrying")
                        wait = 10
                    else:
                        wait = int(r.headers.get("Retry-After", 30 * (attempt + 1)))
                        log(f"  HTTP {r.status_code} on rows {b0}:{b1}; waiting {min(wait, 900)} s")
                    r.close()
                except requests.RequestException as ex:
                    wait = 30 * (attempt + 1)
                    log(f"  {type(ex).__name__} on rows {b0}:{b1}; waiting {wait} s")
                time.sleep(min(wait, 900))
            else:
                raise RuntimeError(f"failed rows {b0}:{b1}")
            blk = np.frombuffer(buf, dtype=dt, count=(b1 - b0) * lab["samples"])
            crop = np.ascontiguousarray(blk.reshape(b1 - b0, lab["samples"])[:, col0:col1], dtype=odt)
            fout.seek(hdr + (b0 - row0) * ncol * odt.itemsize)
            fout.write(crop.tobytes())
            fout.flush()
            del blk, crop
            done.add(b0)
            json.dump(sorted(done), open(ckpt, "w"))
            nbytes += want
            el = time.time() - t0
            log(f"  rows {b0 - row0:>6}-{b1 - row0:<6} of {nrow}  "
                f"{nbytes / 1e9:6.2f} GB  {nbytes / 1e6 / max(el, 1e-6):6.1f} MB/s")
            time.sleep(pause)
    return np.load(out_npy, mmap_mode="r")


def fetch_text(url, session=None):
    s = session or requests.Session()
    r = s.get(url, timeout=120)
    r.raise_for_status()
    return r.text


_IMG_RE = re.compile(r"\b(M\d{9,10}[LR][EC]?)\b")


def parse_image_list(txt):
    """Return NAC product ids (e.g. M1234567890LE) found in an LROC *_IMAGES.TXT."""
    return sorted(set(_IMG_RE.findall(txt)))


def browse_geotransform(relpath_tif):
    """Read (ulx, uly, res_x, res_y, width, height) from a remote LROC browse GeoTIFF header."""
    import rasterio
    url = "/vsicurl/" + PDS_CLOUD + relpath_tif
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR"):
        with rasterio.open(url) as d:
            t = d.transform
            return t.c, t.f, t.a, -t.e, d.width, d.height
