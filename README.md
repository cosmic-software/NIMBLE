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

> **Mike, start here:** [Running NIMBLE on your home computer, step by step](#mike-running-nimble-on-your-home-computer-step-by-step)

## Mike: running NIMBLE on your home computer, step by step
These steps assume no programming background. They are written for Windows 10/11; Mac notes are at the end.
You type commands into a text window called **PowerShell**. Type or paste each command
exactly as shown and press **Enter**.

### What you need
- About **8 GB of free disk space** for one 20 km patch (4 GB download cache plus 2 GB of results, with room to spare).
- An internet connection. A 20 km patch downloads about 3.6 GB, which takes roughly 5 minutes on a good connection.
- 8 GB of RAM or more is comfortable. On a smaller machine, see "If something goes wrong" below.

### Step 1: Install Python (one time only)
1. Go to <https://www.python.org/downloads/> and click the big yellow **Download Python 3.x** button.
   Any version from 3.11 up works.
2. Run the downloaded installer. **On the first screen, tick the box "Add python.exe to PATH"**
   at the bottom. This is the step people most often miss. Then click **Install Now**.
3. When it finishes, click **Close**.

### Step 2: Download NIMBLE (one time only)
1. Go to <https://github.com/cosmic-software/NIMBLE>.
2. Click the green **Code** button, then **Download ZIP**.
3. Open your Downloads folder, right-click `NIMBLE-main.zip`, choose **Extract All…**, and extract it
   somewhere easy to find, for example `C:\NIMBLE`. You should end up with a folder that contains
   `README.md` and a folder called `nimble`. (Sometimes Windows nests it as `C:\NIMBLE\NIMBLE-main`;
   use whichever folder actually contains `README.md`.)

### Step 3: Open PowerShell in that folder
1. Open the folder that contains `README.md` in File Explorer.
2. Click in the address bar at the top (where the folder path is shown), type `powershell`, and press Enter.
   A blue or black window opens, already pointed at the NIMBLE folder.

Every later step happens in this window.

### Step 4: Install NIMBLE's helper libraries (one time only)
```powershell
python -m pip install -r requirements.txt
```
A lot of text scrolls by for a minute or two. It's finished when you see `Successfully installed ...`.

Optional check that the math is right on your machine:
```powershell
python tests\test_geometry.py
```
You should see `round trip ok` and a 20 km edge measured as about `19999.7` m.

### Step 5: Cut a patch
This is the command you will use every time. Change the name, latitude, longitude and size to suit:
```powershell
python -m nimble extract --name ConnectingRidge --lat -89.46 --lon -137.08 --size-km 20
```
- `--name`: any name without spaces. Results go into a folder with this name.
- `--lat`: latitude in degrees. v0.1 handles **-88.5 to -90** only (the south polar cap).
- `--lon`: longitude in degrees east. Negative numbers are fine (-137.08 is the same as 222.92 E).
- `--size-km`: width of the square box in km. Start small (for example `5`) to try it out quickly.

Leave the window open while it runs. Progress lines scroll by, and it's done when the prompt
(`PS C:\...>`) comes back. **If it gets interrupted** (closed window, Wi-Fi drop, reboot), run the
exact same command again. It picks up where it stopped instead of starting over.

### Step 6: Find your results
Open the `runs` folder inside NIMBLE, then the folder with your run name. Inside it:
- `*_preview.png`: double-click for a quick look, with a 2 km scale bar and north arrow.
- `*_IoF_float32.tif`: **the file to measure on.** Open it in QGIS or ArcGIS. 1 pixel = 1 m.
  See [Measuring in QGIS](#measuring-in-qgis) below.
- `METHODS_AND_MATH.txt`: how the patch was made and how accurate it is. Open it with Notepad.
- `STRIPS_IN_BOX.csv`: every NAC image strip that touches the box. Opens in Excel.

### Next time
Open the NIMBLE folder, type `powershell` in the address bar (Step 3), and run Step 5 again with
new numbers. Steps 1, 2 and 4 are one-time only.

**Getting a newer version of NIMBLE:** repeat Step 2 into a fresh folder, then Step 4 in that folder.
Copy your old `runs` folder across if you want to keep your results together.

### If something goes wrong
| What you see | What to do |
|---|---|
| `python is not recognized...` or the Microsoft Store opens | Python isn't on PATH. Re-run the Python installer, choose **Modify**, then make sure "Add Python to environment variables" is ticked. Or use `py` in place of `python` in every command. |
| `No module named nimble` | PowerShell isn't in the right folder. Redo Step 3 from the folder that contains `README.md`. |
| `429` or `Too Many Requests` | NASA's server is asking us to slow down. Wait **one full hour**, then run the same command again. It resumes. Don't run several patches at once. |
| `MemoryError`, or the computer becomes very slow | Add `--block-rows 128` to the end of the Step 5 command and run it again. |
| `No space left on device` | Free up disk space. The folder `data\cache` can be deleted after a run has finished; it only holds raw download pieces. |
| Anything else | Copy the whole PowerShell window text (or the `run.log` file in your run folder) and send it to Ben. |

### Mac notes
Install Python from python.org the same way (the Mac installer has no PATH checkbox). Download and
unzip NIMBLE, then open **Terminal**, type `cd ` (with a trailing space), drag the NIMBLE folder onto
the Terminal window, and press Enter. Use `python3` in place of `python`, and forward slashes in
paths (`tests/test_geometry.py`). Everything else is the same.

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
