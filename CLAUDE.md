# NIMBLE — project instructions for Claude

**NIMBLE = NAC Image Mosaic Builder for Landing-site Evaluation.** Ben's working name for it is
"Lunar NearCam Image Mapper". The source camera is the LRO **Narrow Angle Camera (NAC)**.

## People
- **Ben Gavares** (owner, cosmic-software): runs the project and the machine.
- **Mike Aselin**: lunar landing-site specialist and the main science user. He measures rocks and
  debris to hazard-assessment precision. When Mike is in the session, treat his inputs
  (sites, box sizes, accuracy requirements, which strips to trust or reject) as authoritative
  domain requirements, and log them in `MIKE_INPUTS.md` with the date.

## Ground rules
- Accuracy over pretty. Never resample pixels without saying so and recording it in the run
  manifest. The default products are cut on the native 1 m/px grid of the source mosaic, with
  no resampling.
- Every run folder must carry its provenance: `manifest.json`, the source label, the image list,
  `STRIPS_IN_BOX.csv`, `METHODS_AND_MATH.txt`, and `run.log`.
- Back numbers with measured checks rather than assurances. Ben and Mike will ask.
- Be gentle with PDS servers. The PDS cloud (pds.mcp.nasa.gov) returns HTTP 429 with a
  one-hour Retry-After if hammered. Avoid bulk S3 listings; prefer large contiguous range
  requests over many small ones.
- Name any file and the reason before deleting it.

## Layout
- `nimble/`: Python package (`python -m nimble extract --name X --lat .. --lon .. --size-km 20`)
  - `geometry.py`: polar stereographic math (sphere R = 1737.4 km)
  - `pds.py`: PDS4 label parsing and windowed HTTP range extraction
  - `ode.py`: WUSTL ODE footprint queries, so we know which NAC strips touch the box
  - `export.py`: GeoTIFF (science float32 plus 8-bit view) and annotated preview
- `runs/<name>/`: one folder per site/patch with all deliverables
- `data/cache/`: raw extracted windows (.npy, resumable); safe to delete and re-fetch
- `docs/ROADMAP.md`: the plan for turning this into a full tool
- `BIBLIOGRAPHY.txt`, `CITATION.cff`, `CITATION.txt`: cite these in any product
