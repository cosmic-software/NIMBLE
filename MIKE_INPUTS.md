# Mike Aselin — inputs and requirements log

Mike: write here in plain language, or open Claude Code in this folder (`F:\Claude-projects\NIMBLE`)
and say what you need. Claude reads `CLAUDE.md` on startup, knows who you are, and records your
decisions in this file. Each entry gets a date.

## How to ask for a patch
Tell Claude, or add a row below:

| Date | Site name | Center lat | Center lon (E+) | Box size | Purpose / required accuracy | Status |
|------|-----------|-----------:|----------------:|---------:|-----------------------------|--------|
| 2026-10-06 | Connecting Ridge | -89.46 | -137.08 (222.92 E) | 20 x 20 km | Initial test; rock/debris measurement | done (v0.1), see runs/ConnectingRidge |

## Open questions for Mike
1. **Minimum rock size.** What is the smallest rock you need to count? The 1 m/px mosaic supports
   roughly ≥2–3 m boulders by outline, and smaller ones via shadow length. Sub-meter work means
   going to individual native-resolution NAC frames (~0.5 m/px at the pole for some orbits).
   That is the Phase 2 path in `docs/ROADMAP.md`.
2. **Illumination preference.** At −89.5° the sun never gets more than about 2.1° above the horizon (1.54° max declination + 0.54° colatitude), so
   shadows are long, and that is useful for height-from-shadow. Do you want one consistent sun azimuth
   across the patch (fewer, longer-shadow images) or the most-illuminated composite?
3. **Absolute vs. relative accuracy.** Is ±tens-of-metres absolute placement acceptable as long
   as relative (within-patch) measurements are good? Or do we need to tie to the LOLA 5 m
   south-pole DEM for absolute control?
4. **Output formats** you work in: GeoTIFF in ArcGIS/QGIS, JMARS, Socet, or something else?
5. **Orientation.** Patches are aligned to the polar stereographic grid, which avoids resampling.
   A north arrow is on the preview. Do you prefer a "north-up" local frame, at the cost of one resample?

## Decisions log
- *(empty: Mike's decisions go here)*
