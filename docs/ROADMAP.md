# NIMBLE roadmap: from script to landing-site measurement tool

## What's wrong with the current options
| Tool | What it's good at | Why it fails Mike's job |
|---|---|---|
| **LROC QuickMap** (web) | Browsing every NAC strip, quick looks | Browser-only. Exports are rendered or 8-bit tiles. No provenance trail. Measurement is click-and-eyeball. Can't batch, script, or reproduce a result. |
| **STK** | Orbits, access, comm/lighting analysis | Not an imagery-measurement tool. Imagery is a texture, not a calibrated raster. Licence-heavy. |
| **ISIS (USGS)** | The reference pipeline: calibration, SPICE, orthorectification, control networks | Linux/macOS only, steep learning curve, one command per step, no measurement UI. |
| **ArcGIS / QGIS** | Measuring on a georeferenced raster | Only as good as the raster you bring in. Lunar polar CRSs and NAC provenance are left to you. |

**The gap:** nothing goes from "here is a lat/lon and a box size" to "here is a 1 m (or 0.5 m) per pixel
image with known geometry, known sun angles per pixel, a list of exactly which NAC frames built it,
and tools to measure rocks with error bars," on Windows and reproducibly. NIMBLE fills that gap.

## Design principles
1. **Provenance is a feature.** Every pixel traces back to a NAC frame ID, a time, a sun
   azimuth and elevation, and a processing chain. Mike can defend any number in a review.
2. **No silent resampling.** Measurement products stay on their native grid. Any reprojection is
   explicit, logged, and uses a documented kernel.
3. **Error bars on everything.** Each measurement reports absolute and relative position error,
   pixel-scale uncertainty, and the error in shadow-derived height.
4. **Windows-native Python.** No WSL required for core paths. Heavy ISIS steps can run in Docker
   or WSL as an optional backend.
5. **Talk to it.** A CLI and Python API designed so Claude (driven by Ben or Mike) can run a
   whole study from a sentence.

## Phases

### Phase 1: Controlled-mosaic patches (v0.1, done; v0.2 next)
- [x] Polar stereographic math, PDS4 label parsing, windowed HTTP range extraction (resumable)
- [x] Science GeoTIFF (float32 I/F) + 8-bit view GeoTIFF + preview with scale bar and north arrow
- [x] Strip provenance: ODE footprints ∩ box ∩ LROC mosaic image list → `STRIPS_IN_BOX.csv`
- [ ] All NAC_POLE_SOUTH/NORTH rings (P860/P870/P880), plus boxes that straddle tiles (multi-tile stitch)
- [ ] Sub-solar-longitude mosaics (`NAC_POLE_SOUTH_CM_xxx`) so Mike picks lighting azimuth
- [ ] NAC_ROI controlled mosaics (Shackleton peak, de Gerlache rim, Malapert, Nobile, ...) and
      NAC DTMs (`SDP/NAC_DTM`) where they exist
- [ ] Per-pixel "which strip" map, if LROC exposes it; otherwise reconstruct from footprints + seams

### Phase 2: Native-resolution strip pipeline (the real upgrade)
The polar mosaic is resampled to 1 m. Many south-pole NAC frames are **0.5–0.9 m/px** native.
For rocks under about 3 m, Mike needs the native frames.
- Select frames by footprint ∩ box, native resolution, incidence/phase, sun azimuth, and date.
- Download CDRs (radiometrically calibrated I/F) per frame.
- Camera model plus SPICE: `ale` + `usgscsm` (conda-forge, works on Windows), or ISIS `spiceinit`
  in Docker.
- **Orthorectify on the LOLA 5 m south-pole DEM** (Barker et al. 2021). At the pole, NAC
  look angles and terrain relief on ridges can produce tens of metres of displacement if you
  ignore the DEM.
- **Co-register** each frame to the controlled mosaic (feature matching, sub-pixel phase
  correlation) and record the residual shift as a quality metric.
- Output **one ortho per frame** plus an optional seamline mosaic. Measurements are taken
  on a single frame, never across a blend seam.
- Per-pixel sun azimuth and elevation from SPICE at the frame time, needed for shadow heights.

### Phase 3: Measurement workbench (Mike's daily driver)
- Viewer: Cloud-Optimized GeoTIFFs in a polar-aware viewer (napari plugin or a local web UI with
  OpenLayers in IAU_2015:30135). Instant zoom on 20k × 20k px.
- Click-measure: rock long and short axis, geodesic length, area. Errors are propagated from pixel
  scale, co-registration residual, and DEM-induced displacement.
- **Height from shadow:** h = L_shadow · tan(e_sun) − slope correction from the DEM. At the pole,
  e_sun is about 0.5–2°, so a 1 m rock casts a 30–100 m shadow. NIMBLE's unfair advantage at the
  poles is that tiny rocks show up as long shadows.
- Automated boulder detection: start classical (shadow segmentation plus sun-vector geometry),
  then add an ML detector trained on Mike's labels. Mike's corrections become training data.
- Statistics: size–frequency distributions, cumulative fractional area (Golombek & Rapp 1997
  model fits), rock density per hectare, nearest-neighbour hazard spacing.
- Hazard maps: rock density + DEM slope (LOLA / NAC DTM) + illumination → lander-footprint
  safe-probability map, exported as GeoTIFF + PDF report.

### Phase 4: Packaging and collaboration
- `pip install nimble-lunar`, with a single `nimble` CLI and a Python API.
- GUI shell (Qt or local web app) around the CLI; projects saved as folders with a
  `nimble.toml` + manifest so another analyst can reproduce a result bit-for-bit.
- Exports: GeoTIFF/COG, Shapefile/GeoPackage for rock catalogs, CSV, PDF report, KMZ, and JMARS-compatible layers.
- GitHub repo under cosmic-software, with CI tests against known sites (e.g. Apollo 15/17 landing
  sites, where ground truth exists).

## Accuracy budget (what the numbers actually mean today)
| Source | Typical size | Notes |
|---|---|---|
| Polar stereographic scale error at 89.46°S | 22 ppm (0.4 m over 20 km) | negligible; computed in METHODS_AND_MATH.txt |
| Mosaic pixel scale | 1.00 m | rocks ≲2–3 m are not resolvable by outline |
| Mosaic absolute position | metres to tens of metres (per LROC; see README) | doesn't affect relative rock size |
| Seams between strips | can offset features by a few px | measure away from seams (Phase 2 fixes this) |
| Shadow-height error | dominated by σ(e_sun) and slope | needs Phase 2 per-pixel sun geometry |

## Immediate next steps (suggested)
1. Mike reviews the Connecting Ridge patch and answers the questions in `MIKE_INPUTS.md`.
2. v0.2: multi-tile stitching + CM (lighting-binned) mosaics + NAC DTM overlay if one exists.
3. Spike Phase 2 on 2–3 of the highest-resolution frames from `STRIPS_IN_BOX.csv`, and
   compare rock counts against the 1 m mosaic.
