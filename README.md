# NIMBLE: NAC Image Mosaic Builder for Landing-site Evaluation
*a.k.a. the Lunar NearCam Image Mapper*

Give NIMBLE a lunar lat/lon and a box size. It returns a measurement-grade, georeferenced
**1 m/pixel LRO Narrow Angle Camera (NAC)** image patch, plus the provenance needed to defend
every number taken from it:
- the exact source product and pixel window
- every NAC strip that touches the box
- the projection math, with error budgets
- a bibliography and citation

**Authors:** Ben Gavares (cosmic-software), Mike Aselin (lunar landing-site specialist), and Claude (Anthropic).

## What it does
1. Picks the LROC South Pole NAC mosaic tile (`NAC_POLE_SOUTH`, 1 m/px, polar stereographic)
   that contains your point, and downloads its PDS4 label.
2. Converts your lat/lon and box size to a pixel window on the mosaic's native grid
   (sphere R = 1737.4 km, IAU_2015:30135), and cross-checks the georeference against the
   LROC browse GeoTIFF.
3. Downloads **only that window**, using HTTP range requests in large contiguous blocks.
   The download is checkpointed, so an interrupted run resumes where it stopped.
4. Writes GeoTIFFs **without resampling**, queries WUSTL ODE for every NAC frame whose
   footprint touches the box, and writes a methods report with the math and accuracy for
   that patch.

## Install (Windows, Python 3.11+)
```powershell
git clone https://github.com/cosmic-software/NIMBLE.git
cd NIMBLE
python -m pip install -r requirements.txt
python tests\test_geometry.py        # checks the projection math against PROJ
```
Dependencies: numpy, requests, rasterio, pyproj, shapely, Pillow. All of them install
as binary wheels on Windows; no GDAL or conda setup is needed. Linux and macOS work the same way.

## Cut a patch
```powershell
python -m nimble extract --name ConnectingRidge --lat -89.46 --lon -137.08 --size-km 20
```

| Option | Meaning |
|---|---|
| `--name` | Run name. Output goes to `runs\<name>\`. Re-running the same name resumes the download. |
| `--lat` | Centre latitude in degrees. v0.1 supports the polar cap, **−88.5° to −90°**. |
| `--lon` | Centre longitude, degrees **east-positive**. Negative values are fine (−137.08 = 222.92 E). |
| `--size-km` | Side length of the square box, in km (default 20). A 20 km box is 20000 × 20000 px, about 1.6 GB of float32. |
| `--tile` | Force a specific source product (e.g. `NAC_POLE_P892S2250`) instead of auto-picking. |
| `--block-rows` | Rows per HTTP range request (default 512, about 93 MB per block). Lower it on a low-memory machine. |

Regenerate the methods report for an existing run without downloading anything:
```powershell
python -m nimble report --name ConnectingRidge
```

**Time and space.** A 20 km box downloads about 3.6 GB (whole mosaic rows are fetched, then
cropped) at the server's pace, typically 13–17 MB/s, so about 4–5 minutes. Budget about
4 GB on disk for the cache plus about 2 GB per run folder. The download cache
(`data\cache\*.npy`) can be deleted once a run has finished.

## Outputs
Everything lands in `runs\<name>\`:

| File | Use |
|---|---|
| `*_IoF_float32.tif` | **Measure on this.** Exact LROC I/F values, unresampled, CRS IAU_2015:30135, tiled + overviews. Opens in QGIS/ArcGIS. |
| `*_8bit.tif` | Same grid, display stretch, for fast viewing |
| `*_preview.png` | Overview with 2 km scale bar and north arrow |
| `METHODS_AND_MATH.txt` | Equations, the numbers for this patch, accuracy, source strips |
| `STRIPS_IN_BOX.csv` | Every NAC frame touching the box, with sun/view angles and `in_mosaic` flag |
| `manifest.json`, `run.log`, LROC label/README/image list | Full provenance |

Run folders are not committed to this repository because they are multi-GB. Each one can be
reproduced from the command line recorded in its `manifest.json`.

## Measuring in QGIS
1. Drag `*_IoF_float32.tif` into QGIS. The layer carries its lunar polar stereographic CRS;
   set the project CRS to match (Project ▸ Properties ▸ CRS ▸ the layer's CRS) so distances are metric.
2. Use the Measure Line tool. Patches are on the native mosaic grid, so 1 pixel = 1.000 m.
3. Image "up" is **not** north near the pole. Use the north arrow on the preview, or
   `north_azimuth_deg_cw_from_image_up` in `manifest.json`.
4. Check `STRIPS_IN_BOX.csv` before trusting a measurement that crosses a visible seam;
   features can be offset by a few pixels between strips.

## Accuracy, in brief
- Pixel scale: 1.00 m. Rocks under about 2–3 m are not resolvable by outline.
- Projection scale error at 89.46°S: 22 ppm (0.4 m over 20 km).
- Absolute placement: metres to tens of metres (per LROC). Relative, within-patch measurements are much better.
- Full budget: `docs/ROADMAP.md` and each run's `METHODS_AND_MATH.txt`.

## Working with Claude
Open a terminal in this folder and run `claude`. It reads `CLAUDE.md` (project rules) and
`MIKE_INPUTS.md` (Mike's requests and decisions). Then just talk, for example:
- "Cut a 10 km box at de Gerlache Rim 2, same settings."
- "Which strips in the Connecting Ridge box have native resolution better than 0.6 m?"
- "Reject M1234567890L, it has smear. Log that."

## Being gentle with PDS
The NASA PDS cloud returns HTTP 429 with a one-hour Retry-After if it is hammered. NIMBLE
uses a few large range requests per run and backs off on errors. Please don't run many
extractions in parallel.

## Status
v0.1: polar cap tiles (−88.5° to −90°) of the LROC South Pole NAC mosaic. See `docs/ROADMAP.md`
for the path to native-resolution strips, DEM orthorectification, shadow heights, and automated
boulder counting.

## Cite
See `CITATION.txt` / `CITATION.cff` and `BIBLIOGRAPHY.txt`. Always credit the LROC data:
*"LROC NAC imagery courtesy NASA/GSFC/Arizona State University."*

License: MIT, Copyright (c) 2026 Ben Gavares, Owner, cosmic-software.
