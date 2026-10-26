# Model Village: project plan (draft for review)

Status: **plan only, awaiting your approval**. The one piece of code so far is the Phase 0 proof-of-concept script in `poc/`, which you asked for as part of the plan.

Researched 25 October 2026. Wherever this plan says **verified**, I ran a real request from this environment against the live service. Anything marked **unverified** is something I could not confirm and you should treat with suspicion.

---

## 1. Headline verdict

**Go.** The core idea is very achievable, and easier than you might expect:

- The Environment Agency (EA) runs a free, public **WCS** (Web Coverage Service: a standard web API that returns a raster for exactly the box you ask for) for its 1m LIDAR composites. I pulled real 100m and 500m boxes in about 1 to 1.5 seconds each. No tile downloads or caching are needed for the 1m data.
- The proof-of-concept script turns a latitude/longitude into a **watertight** STL (a closed solid with no holes, which slicers need) in about 5 seconds for a 500m square. Tested on York Minster, Thirsk, Ripon, a stretch of Whitby coast and a point out at sea.

But I'm pushing back on four of your assumptions:

1. **50m squares will look like Lego.** At 50m printed 170mm wide, each 1m data cell is 3.4mm across. Your house would be roughly 8 x 10 blocks. 100m is the practical minimum at 1m resolution; 150 to 400m is the sweet spot.
2. **Don't count on 50cm or 25cm data.** It exists, but only in patches (mostly older flood-risk surveys along rivers and coasts). At York Minster the 50cm tile covers only a strip along the river, about 19% of the tile, and not the Minster.
3. **The point clouds won't beat the 1m rasters.** I measured the National LIDAR Programme point cloud at York: about **2.6 points per m²** (1.9 first returns per m²). That's roughly one point every 60 to 70cm, so you can't make a meaningfully sharper grid from it.
4. **Google's photorealistic 3D tiles are off limits.** They'd look amazing, but Google's terms ban offline use and extracting geometry. More in section 2.1.

Expect your house to be recognisable as a block with a roof ridge and pitch, neighbours' houses, gardens and trees as blobs. You won't get chimneys, windows, porches, fences or cars as identifiable objects. Also, the data is from 2000 to 2022 (York's tile is from a 2020/21 survey), so a recent extension may be missing.

---

## 2. Phase 0: feasibility findings

### 2.1 Data source survey (go/no-go: **GO**)

| # | Source | What and resolution | Coverage | Data age | Cost | Licence: can I export and print it? | Small bounding box? | Verdict |
|---|---|---|---|---|---|---|---|---|
| 1 | **EA LIDAR Composite 1m** (DTM, First Return DSM, Last Return DSM) | 1m rasters, vertical accuracy ±15cm RMSE | ~99% of England | Surveys 2000 to April 2022 (2022 composite) | Free | OGL: yes, including commercial use, with attribution | **Yes, WCS 2.0.1, GeoTIFF, EPSG:27700. Verified.** Also sends `Access-Control-Allow-Origin: *`, so a browser can call it directly (verified) | **Primary** |
| 2 | **EIDC merged England and Wales 1m DTM/DSM** (published 7 Aug 2026) | 1m Cloud Optimised GeoTIFFs, int32 **millimetres** | England + ~70% of Wales | Same as #1 for England | Free | OGL, plus cite the dataset | **Yes, HTTP range reads of one ~310GB COG. Verified.** Values matched #1 exactly at York | **Fallback** |
| 3 | EA National LIDAR Programme 1m (per survey: DSM, DTM, First Return DSM, intensity, Vegetation Object Model) | 1m rasters | All England | 2017 to 2023 programme, repeats since | Free | OGL | Whole 5km tile zips only (undocumented search API, verified) | Not needed; #1 already includes it |
| 4 | EA NLP point cloud (LAZ) | ~2.6 pts/m² at York (measured), classified incl. ground, vegetation, buildings | All England | As #3 | Free | OGL | Whole 5km tile zips only, ~230MB each (verified) | No: not sharper than #1 |
| 5 | EA time-stamped 50cm / 25cm tiles and composites | 50cm and 25cm rasters | Patchy; one source says over 75% of England has *some* LIDAR, but high-res is mostly rivers and coasts | Varies, often 2000s to 2010s | Free | OGL | 50cm via whole tile zips (~49MB for a 5km tile, verified). No WCS found for 50cm/25cm (tried the obvious URLs, 404) | Optional enhancement later, with caching |
| 6 | OS Terrain 5 | 5m DTM (bare earth only) | GB | Updated quarterly | Paid (Premium) | Licence via OS / partners | 5km tile download | No: coarser than free #1 |
| 7 | OS 3D Mesh (beta) | Photogrammetry mesh from 15cm imagery, Cesium 3D Tiles / SLPK | Made to order | 3-year imagery cycle | Not published | Not published; beta, "not maintained" | Made-to-order download | Interesting, not currently usable |
| 8 | Google Photorealistic 3D Tiles | Photogrammetry mesh | Most UK towns | Varies | Pay per use | **No.** Policies ban "offline uses", "geodata extraction" and caching | Streaming only | **Ruled out** |
| 9 | Bluesky (commercial) | 25cm DSM, but listed vertical accuracy **±1m RMSE** (worse than EA's ±15cm) | GB | Varies | Quote only; "from £20 to ~£50,000" | Commercial licence, terms by quote | Order by quote | Not worth it for a hobby |
| 10 | Getmapping (commercial) | DSM / imagery | GB | Varies | Not published | Licences seen elsewhere restrict to internal use | Order by quote | Not worth it |
| 11 | Copernicus GLO-30 / FABDEM | 30m global | Global | ~2011 to 2015 | Free (FABDEM free for non-commercial use only) | Open-ish | COG tiles | No: a 100m square would be ~3 x 3 pixels |
| 12 | Wales: NRW all-Wales LIDAR | 1m DTM/DSM as all-Wales COGs | Wales | Capture years not confirmed (a filename suggests 2020 to 23) | Free | OGL | COG range reads (same code path as #2) | Plugs in later |
| 13 | Scotland: Scottish Remote Sensing Portal | 50cm to 1m DTM/DSM by phase, plus LAS | Partial (phase by phase, not national) | 2011 to 2022-ish | Free | Mostly OGL v3, some exceptions | 10km tile downloads + WMS | Plugs in later, with caching |

**Building footprint sources** (for question 4):

| Source | What | Licence | How to fetch | Notes |
|---|---|---|---|---|
| OpenStreetMap | Footprints; heights only sometimes tagged | ODbL | Overpass API (query by bbox) or Geofabrik county extract | Best free option. **Unverified at York:** Overpass failed from this environment (timeouts/502s), which is itself a reliability warning |
| OS OpenMap Local | Generalised footprints (1:10,000) | OGL | Download from OS Data Hub | Terraces often merged into one block; outlines simplified |
| OS NGD Buildings | Accurate footprints plus height attributes (added March 2025) | Premium | OS NGD API Features, £0.19 per request of up to 100 features | Premium plan is for OS Partners building services for others, not individuals. Not realistic for you |
| Overture Maps buildings | Global footprints, some heights | ODbL | GeoParquet on S3 | Largely derived from OSM in the UK; no advantage |

**Recommendation**

- **Primary:** EA LIDAR Composite 1m via WCS. Free, fast, any box, no caching needed.
- **Fallback:** EIDC merged COG, read by HTTP range requests (only downloads the bytes for your box). Same data, different host, so it protects you if the EA endpoint changes. **Gotcha I found:** EIDC stores heights as whole millimetres and its "DSM" is the *first return* DSM; neither fact is obvious from the metadata.
- **Later, optional:** 50cm/25cm time-stamped tiles where they exist, downloaded whole and cached on disk.

### 2.2 Licensing, attribution and rate limits (go/no-go: **GO**)

- **EA data:** [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/). You may copy, adapt, print and even sell derived works, provided you attribute. Required text from the dataset record: *"© Environment Agency copyright and/or database right 2022. All rights reserved."* Show it in the app, and consider embossing "Contains EA LIDAR data" on the underside of prints you give away.
- **EIDC:** OGL, and they ask you to cite the dataset (DOI 10.5285/34443359-64c0-4909-9f27-bb5d47f1153f) in publications.
- **OpenStreetMap (if used):** ODbL. A 3D print is a "Produced Work". OSMF guidance says attribution is required when a produced work is used publicly; for a print on your own shelf it isn't strictly needed, but if you share STLs online (e.g. Printables), credit "© OpenStreetMap contributors". Merging OSM footprints with EA heights is fine for personal use; if you ever publish the *merged dataset* (not the print), ODbL share-alike applies.
- **OS OpenData (OpenMap Local, basemap):** OGL. Attribution "Contains OS data © Crown copyright and database right [year]".
- **Rate limits:**
  - EA: no published limit found. There is a "Fair Use Policy" page on the Defra support site but it's JavaScript-rendered and I couldn't read its contents (**unverified**). One person making occasional requests is negligible, but the app will still cache every response on disk and send a descriptive User-Agent.
  - Overpass (OSM): guideline of roughly 10,000 requests and 1GB per day per application, ~100 a day for regular automated use. Fine for you. It failed repeatedly from here, so the plan uses a local Geofabrik extract as a fallback.
  - Google 3D tiles: excluded, see above.

### 2.3 Best product type (go/no-go: **GO, First Return DSM by default**)

Real numbers from a 100m box at York Minster:

| Product | Height range | What it is |
|---|---|---|
| DTM | 15.19 to 16.55m | Bare earth. Buildings and trees removed, gaps filled by interpolation |
| Last Return DSM | 15.19 to 77.15m | Surface from the *last* laser echo. Laser partly penetrates trees and clips building edges |
| First Return DSM | 15.23 to 77.21m | Surface from the *first* echo: tops of trees, roofs, and anything else |

First vs last return differed by up to **31m** (mean 2.3m) within that one box, mostly in trees and at building edges.

- **First Return DSM (default):** solid tree canopies, fullest building outlines. Downsides: trees look like blobs, plus occasional spikes from cranes, wires or birds (needs a spike filter).
- **Last Return DSM:** ragged, see-through-looking trees and nibbled building edges. Not recommended.
- **DTM:** the right choice for landscape models (hills, valleys) where buildings are noise. Usually needs vertical exaggeration in flat North Yorkshire lowland; Thirsk's 300m box only varies by 10m.
- **Combination (recommended for later milestones):** DSM minus DTM gives a "normalised" height above ground. That lets you: flatten or shorten trees, remove spikes, classify cells as ground / building / vegetation for colour prints, and sit footprint-sharpened buildings on true ground level.
- **Point cloud:** not worth it (see section 1).

### 2.4 Do building footprints help? (go/no-go: **GO for areas up to ~250m, as a later milestone**)

Yes, meaningfully, at small areas. At 1m resolution a building wall falls somewhere inside one cell, so the mesh joins roof to ground with a sloped triangle 1 cell wide. At 100m that's a 1.7mm-wide slope, so walls look melted and jagged in plan. The approach:

1. Rasterise footprint polygons onto a finer grid (e.g. 25cm).
2. Outside footprints: use the ground (DTM, or DSM for trees).
3. Inside footprints: use roof heights from the DSM, sampled away from the edges to avoid the blurred boundary cells.
4. Result: vertical walls and crisp, straight building edges.

Caveats: OSM footprints may be missing or slightly misaligned; buildings built after the LIDAR survey will have a footprint but no height (or vice versa); trees overhanging roofs confuse roof heights. At 500m the gain is small because each 1m cell is already smaller than the nozzle.

Licensing: OSM (ODbL) or OS OpenMap Local (OGL), as above.

### 2.5 What detail is achievable? (go/no-go: **GO, with realistic expectations**)

Assumptions: printed width 170mm, 0.4mm nozzle. A 0.4mm nozzle extrudes lines about 0.42mm wide; the smallest reliable free-standing wall is about two lines (~0.8mm). (Printer limits are general 3D printing knowledge, not something I verified.)

| Area | mm per metre | Scale | 1m cell on print | 50cm cell | 25cm cell | Limiting factor | What you'll see |
|---|---|---|---|---|---|---|---|
| 50m | 3.4 | 1:294 | 3.4mm | 1.7mm | 0.85mm | Data, badly | Blocky. A house is ~8 x 10 steps |
| 100m | 1.7 | 1:588 | 1.7mm | 0.85mm | 0.43mm | Data | House shapes, roof pitch and ridge, garden trees. No chimneys or windows. Walls jagged without footprints |
| 200m | 0.85 | 1:1176 | 0.85mm | 0.43mm | (below nozzle) | Data, roughly matched to printer | Streets, individual houses, gardens |
| ~380m | 0.45 | 1:2235 | 0.45mm | (below nozzle) | | **Crossover:** 1m data ≈ nozzle | Best use of 1m data |
| 500m | 0.34 | 1:2941 | 0.34mm | | | Printer | Town plan; a two-storey house is only ~2.7mm tall at true scale |

Heights are much less of a problem than plan detail. Vertical accuracy of ±15cm is 0.26mm at 100m, about two fine layers. At true scale York Minster's 100m box comes out 109mm tall, which fits the 180mm build height.

**Tip:** for a single house, print a 100 to 150m square smaller (e.g. 100mm wide). It looks less blocky than the same area at 170mm, and prints faster.

**Practical warning:** tall urban models are big solids. The Minster box is 975cm³ solid; the slicer fills it with sparse infill, but it will still be a long print. Flatter suburban areas are much lighter (Ripon 500m: 278cm³ solid).

### 2.6 Proof-of-concept script (go/no-go: **GO, working**)

`poc/make_stl.py` does: lat/lon → British National Grid square → EA WCS GeoTIFF → height grid → solid mesh (top surface + 4 walls + flat base) → STL.

Test runs from this environment:

| Run | Result |
|---|---|
| York Minster, 100m, First Return DSM | 100 x 100 grid, 170 x 170 x 109mm, 20,790 triangles, watertight |
| Thirsk, 300m, DTM, 3x exaggeration | 170 x 170 x 20mm, 182,390 triangles, watertight |
| Ripon, 500m, First Return DSM | 170 x 170 x 19mm, 503,990 triangles, watertight, ~5s total |
| Whitby coast, 500m (part sea) | Filled 115,034 no-data cells with lowest height, watertight |
| English Channel | Correctly reports "No LIDAR coverage" |

Testing found two behaviours worth knowing: (a) wholly outside the survey, the WCS returns all zeros with no "no data" flag, so the script checks for that; (b) a large sea area defeated interpolation-based gap filling, so gaps are filled with the lowest valid height instead.

**To run it on your machine** (needs Python 3.11+):

```bash
cd poc
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python make_stl.py --lat 53.9623 --lon -1.0819 --size 100 --out minster.stl
python make_stl.py --help        # all options: --product dsm|dsm-last|dtm, --width, --exaggeration, --base
```

New things in there: **venv** is Python's built-in way to keep a project's libraries separate from the rest of your system. **pyproj** converts coordinates between systems. **rasterio** reads GeoTIFFs (images whose pixels are heights, plus location metadata). **trimesh** builds and checks 3D meshes and writes STL.

**Milestone 1's acceptance test is yours**, because I can't run Bambu Studio here: open the STL, check Bambu Studio reports no errors, slice it, and ideally print a small one.

### 2.7 Test case: Leeds city centre (tall buildings)

Checked against a 2.2 x 2.4km box of real data (26 October 2026). This becomes a standing regression test (see M2).

**Heights are accurate:**

| Building | Published height | In the data (first-return DSM minus DTM) |
|---|---|---|
| Sky Plaza | 106m | 104.8m |
| Bridgewater Place | 112m | 107m at the highest 1m cell (its sloping crown narrows to a point thinner than a cell) |

**Walls are near-vertical:**

- Profiles through both towers drop from ~100m to ground in 1 to 3 cells. On Bridgewater Place's north side the drop is one cell (104m, then 0m).
- On a 300m print, a 100m tower is ~57mm tall and its walls lean by at most 0.6 to 1.7mm: 88 to 89 degrees, which looks vertical.
- Tall buildings fare better than the low houses in section 2.5.
- Setbacks and podiums survive; Bridgewater Place's step down to its ~35m lower block is clear.

**Limits:**

- Outlines are stair-stepped at 1m. About half the cells next to walls hold blended mid-height values, giving a slight bevel at the top and bottom of the wall.
- Anything thinner than ~1m (spires, masts, fins) is lost or shortened.
- Overhangs and cantilevers print as solid, because the data is a heightfield (one height per point).

**Data age is the real problem:**

- The newest survey covering the city centre is the 2019 National LIDAR Programme.
- Missing entirely: Arena Point / Cirrus Point (134m, 2025), Jackson House (100m, 2024) and Latitude Blue (98m, 2025).
- The Arena Quarter around Altus House (114m, completed 2021) is captured as a building site, with spikes up to 161m above ground that are almost certainly tower cranes.
- Hence the spike filter in M2, and the missing-buildings feature in section 3.7 and M7.

**Practical settings:** 300 to 500m squares and 1x exaggeration. Leeds centre's ground falls ~37m from north to the river, so the 180mm build height is no constraint at these sizes.

Source for published heights: [List of tallest buildings and structures in Leeds (Wikipedia)](https://en.wikipedia.org/wiki/List_of_tallest_buildings_and_structures_in_Leeds).

---

## 3. App design (Phase 1 onwards)

### 3.1 Architecture

```
Browser (one static HTML page)              Local Python server (your machine)
------------------------------              ----------------------------------
Leaflet map + square overlay   --request--> /api/model?lat&lon&size&options
three.js 3D preview            <--STL/3MF-- 1. lat/lon -> BNG square (pyproj + OSTN15)
Download button                             2. fetch heights (EA WCS, disk cache)
                                            3. optional: footprints, filters
                                            4. build solid mesh (numpy + trimesh)
                                            5. export STL / 3MF
```

- **Backend: Python with FastAPI** (a small, popular Python web framework). Why a backend at all? It reuses the proof-of-concept code directly, and the Python geospatial and mesh libraries are far more mature than their JavaScript equivalents. It also gives you a disk cache.
- **Frontend: plain HTML and JavaScript, no build tools.** Libraries load from a CDN via an *import map* (a browser feature that lets you `import` libraries by name without a bundler). Fewer moving parts for a beginner.
- Run with one command (`uvicorn app:app`) and open `http://localhost:8000`.
- **Future option:** because the EA WCS allows cross-origin requests, the whole thing could later move into the browser and be hosted free (e.g. GitHub Pages). Not for v1.

### 3.2 Coordinate handling

- EA data is in **British National Grid** (EPSG:27700: metres east/north on the OSGB36 datum). Web maps use **WGS84** latitude/longitude (EPSG:4326), displayed in Web Mercator (EPSG:3857).
- **The model square is defined in BNG**, aligned to the 1m grid, so it lines up exactly with the data cells. Nothing gets resampled.
- Backend converts with **pyproj**. **Important detail I verified:** without extra data, pyproj uses an approximate conversion (accurate to ~2m). With the official **OSTN15** grid file (3MB, free from cdn.proj.org), it's ~0.1m accurate. At York the two differ by about 2m, which is visible on a 100m model. The app will bundle that file. A trap: if pyproj is told to download grids on the fly and the download fails, it silently returns `inf`, so the code must check for that.
- **Browser** uses **proj4js** (JavaScript equivalent of pyproj) only to draw the square's four corners on the map. Because the BNG grid is not aligned with true north, the square appears rotated by under 1° around York and up to about 3° at England's far east and west edges. This is correct, not a bug.

### 3.3 Mesh generation

Already working in the proof of concept:

- **Top surface:** one vertex per 1m cell, two triangles per cell.
- **Walls:** four sides joining the edge of the surface down to z = 0.
- **Base:** flat, closed with a fan of triangles from the centre.
- **Sizing:** horizontal scale = print width / area width. Vertical scale = the same × exaggeration.
- **Base thickness:** lowest point sits at `--base` mm (default 3mm).
- **Height warning:** warns if the model exceeds the 180mm build volume.

To add:

- **Spike filter:** a median filter on DSM-minus-DTM to kill cranes, wires and birds. Uses scipy (Python's standard scientific library).
- **Tree handling:** keep, flatten to a fixed height, or remove (use the DTM where vegetation is detected).
- **Upsampling:** bicubic 2x or 4x resampling softens the staircase look. Be clear-eyed: it adds smoothness, not detail. Footprint sharpening (section 2.4) is the real improvement.
- **Minimum feature check:** warn when the scale makes 1m cells smaller than ~0.4mm (areas over ~380m), where more data detail is wasted.
- **Mesh decimation** (merging flat triangles) only if files get unwieldy. A 500m square is ~500k triangles, ~25MB STL, which Bambu Studio handles fine.

### 3.4 Map UI

- **Leaflet** (simple, well-documented JavaScript map library) with **OS Maps API** tiles. You need a free OS Data Hub OpenData account and API key; the Light and Outdoor styles look good. OS's docs disagree on the maximum free zoom (16 vs higher, **unverified**), so OpenStreetMap tiles are a backup.
- Click to set the centre. A slider sets size from 50 to 500m (with a warning below 100m), and the square overlay updates live.
- An info panel shows scale, mm per 1m cell, estimated height, and data date if available.
- **Optional overlay:** the EA LIDAR hillshade (also served by the same EA service). It instantly shows what the data looks like and where coverage stops.

### 3.5 3D preview

- **three.js** (the standard JavaScript 3D library) with OrbitControls (mouse rotate/zoom). It loads the exact STL that would be downloaded, so the preview is truthful.
- **"On the bed" view:** the model sits on a to-scale mock of the A1 mini's 180 x 180mm plate, rendered in the chosen filament colour.
  - Optional layer lines at the chosen layer height, so you can judge how fine details and stair-steps will really look.
  - A warning if the model overhangs the plate or exceeds the 180mm build height.
  - A throwaway mock-up of this view (Leeds, 500m, real data) is at https://claude.ai/artifact/KJNUQABjqukiwJLNBvDvAm (private to you).

### 3.6 Export: STL vs 3MF, and colour

- **STL:** just triangles. No units (slicers assume mm), no colour, universally supported. Default for v1.
- **3MF:** a zip of XML files. It carries units, multiple named objects and parts, and colour/material info. It's Bambu Studio's native format.
- **Multi-colour for the AMS Lite: possible, but it's the riskiest milestone.**
  - Classify each cell as ground, building (footprints or DSM-minus-DTM) or vegetation.
  - Generate **separate, non-overlapping solids** for each class that fit together like a jigsaw.
  - Export them as parts of one object in a 3MF. You then assign a filament to each part in Bambu Studio (a few clicks).
  - Auto-assigning filaments means writing Bambu's own `Metadata/model_settings.config` file. That format is undocumented (reverse-engineered by third parties), so it's a stretch goal.
  - Avoid overlapping parts. Which part "wins" an overlap in Bambu Studio is only known from forum anecdote.
- **Simplest colour option, no code:** Bambu Studio's paint tool, or a filament change at a set layer height (e.g. green base, grey above).

### 3.7 Nice-to-haves (later)

- **Plaque:** raised or engraved text on the base or front wall (place name, date, "Contains EA data"). trimesh can extrude text outlines, or use a pre-made font outline.
- **Add missing buildings manually:** for towers built after the survey (e.g. Leeds's Arena Point), you pick a footprint (from OSM, or draw it on the map) and enter a height or take the published one. The app then:
  - flattens the old data inside the footprint to ground level (removing any cranes or building site);
  - raises the footprint as a flat-topped block at that height.
  
  The result is a clean vertical-walled block rather than real roof shape, but it keeps a skyline current. Edits are saved per location so they can be reused. It reuses the footprint rasterising code from M7.
- **Multi-tile prints:** split a larger area (e.g. 1km) into a grid of 170mm tiles with matching edges and a shared base height. Add alignment pegs/holes.
- **Wales:** NRW all-Wales COGs, same range-read code as the EIDC fallback.
- **Scotland:** Scottish Remote Sensing Portal 10km tiles, downloaded and cached. Coverage is partial.
- **50cm/25cm:** use where available via the tile search API, with a disk cache.
- **Coverage-aware source picker:** choose the best source automatically per location.

---

## 4. Recommended tech stack

| Choice | Why |
|---|---|
| Python 3.12+ | The geospatial and mesh ecosystem lives here; the PoC already works in it |
| venv + pip, pinned `requirements.txt` | Built into Python, nothing extra to learn |
| requests | Simplest way to call web APIs from Python |
| numpy | Fast array maths; a height grid is just a 2D array |
| rasterio | Reads GeoTIFFs and Cloud Optimised GeoTIFFs (including partial remote reads) |
| pyproj + OSTN15 grid | Official-accuracy WGS84 ↔ BNG conversion |
| trimesh | Builds, validates (watertight check) and exports STL/3MF meshes |
| scipy | Median/Gaussian filters and resampling for spike removal and smoothing |
| shapely | Geometry operations on building footprints |
| FastAPI + uvicorn | Minimal Python web server with automatic API docs; uvicorn runs it |
| pytest | Standard Python testing; we'll test mesh watertightness and coordinates |
| Leaflet | Simplest web map library; huge community |
| proj4js | Draws the BNG-aligned square correctly on the web map |
| three.js | Standard browser 3D; has a ready-made STL loader |
| OS Maps API (OpenData plan) | Free, UK-specific basemap that's good for spotting houses |

---

## 5. Phased build plan

Each milestone ends with something you can run and check.

| # | Milestone | Done when |
|---|---|---|
| **M1** | **Proof of concept** (drafted and tested here) | You've run `poc/make_stl.py` on your house and another location, opened the STLs in Bambu Studio without errors, and printed one small test (e.g. 100m at 100mm wide) |
| M2 | Turn the PoC into a tidy package: config file, disk cache, OSTN15 bundled, EIDC fallback, spike filter, pytest suite | `pytest` passes: watertight on several locations; coordinate round-trip within 0.1m; fallback produces identical heights; **Leeds test:** Sky Plaza and Bridgewater Place within 5% of published heights, and the Arena Quarter crane spikes removed by the filter. CLI still produces the same STL |
| M3 | Local web server: `/api/model` returns an STL; bare HTML form with lat/lon/size | Download an STL from the browser that matches the CLI output |
| M4 | Map UI: Leaflet, click to place, size slider, rotated BNG square, scale/info panel | Square drawn on map matches the area of the downloaded model (checked against a known landmark) |
| M5 | 3D preview with three.js: model on a to-scale A1 mini plate, filament colour, optional layer lines, size warnings | Preview matches the STL opened in Bambu Studio |
| M6 | Print-quality options: product choice, exaggeration, base thickness, width, tree handling, upsampling; plus a test-print matrix | Side-by-side test prints let you choose sensible defaults |
| M7 | Footprint sharpening (OSM via Overpass, Geofabrik fallback; OS OpenMap Local as alternative), then manually adding missing buildings | A 100m print of your street shows vertical walls and straight edges (compare against M6); a Leeds 500m model includes Arena Point as a 134m block with no crane spikes |
| M8 | 3MF export: single colour first, then ground/building/vegetation parts | Bambu Studio opens the 3MF as one object with 3 parts; you assign filaments and print |
| M9 | Nice-to-haves: plaque text, multi-tile, Wales, Scotland, 50cm/25cm | Per feature |

---

## 6. Risks and unknowns (ranked)

| Rank | Risk | Likelihood / impact | Mitigation |
|---|---|---|---|
| 1 | **Expectation gap:** 1m data at small areas looks blocky; "my house" lacks detail | High / High | Test prints in M1; prefer 150 to 400m; print small areas smaller; footprint sharpening in M7 |
| 2 | **Footprint sharpening is fiddly:** misalignment, missing or out-of-date footprints, trees over roofs | Medium / Medium | Make it optional and per-building tolerant; fall back to raw DSM where footprint and LIDAR disagree |
| 3 | **Multi-colour 3MF:** Bambu-specific metadata undocumented; overlap behaviour unclear | Medium / Medium | Non-overlapping parts; manual filament assignment first; auto-assignment as stretch goal |
| 4 | **EA endpoints change:** coverage IDs contain UUIDs that may change when composites are refreshed; the tile search API is undocumented | Medium / High | IDs in a config file; read them from GetCapabilities on start-up; EIDC fallback; disk cache |
| 5 | **Data age:** surveys up to 2022 (York 2020/21, Leeds centre 2019); new buildings missing; cranes and building sites captured | Certain / Low-Medium (High for fast-changing city centres) | Show survey date in the UI; spike filter; manually add missing buildings (section 3.7) |
| 6 | **Overpass reliability** (failed from here) | Medium / Low | Geofabrik county extract (offline), cache per area |
| 7 | **Print practicality:** tall cities mean long prints and lots of filament; thin spikes (spires, trees, cranes) may fail | Medium / Low | Height estimate and solid volume in UI; spike filter; optional max height cap |
| 8 | **Coordinate accuracy** if the OSTN15 grid isn't loaded (~2m error) | Low / Low | Bundle the grid; test asserts it's in use |
| 9 | **Unpublished EA fair-use limits** | Low / Low | Caching, descriptive User-Agent, one request per model |
| 10 | **Edge cases:** water bodies, coastline, England/Wales/Scotland borders | Medium / Low | Lowest-height fill (done); clear "no coverage" errors; later multi-source |

---

## 7. Questions for you before building

1. **Your computer:** Windows, macOS or Linux? This affects install instructions (rasterio has prebuilt wheels for all three, so it should be painless).
2. **Most important size:** is the main goal "my house at ~100m" or "my village at 300 to 500m"? If it's 100m, footprint sharpening (M7) should move up the list.
3. **Colour:** do you actually have the AMS Lite? Is single colour fine until M8?
4. **Trees:** keep them as blobs, flatten them, or remove them by default?
5. **Sharing:** will you publish models or STLs (Printables, social media), or keep them personal? This only affects attribution text.
6. **Print width:** always ~170mm, or should the app suggest a smaller width for small areas?
7. **OS Data Hub:** happy to create a free OpenData account for the basemap API key? If not, we use OpenStreetMap tiles.
8. **Repository:** shall I commit this plan and the PoC to this repo, and on which branch? Nothing is committed yet.

---

## 8. Sources

**Verified by live requests from this environment (25 Oct 2026):**

- EA WCS endpoints (GetCapabilities and GetCoverage): `https://environment.data.gov.uk/spatialdata/lidar-composite-digital-terrain-model-dtm-1m/wcs`, `.../lidar-composite-digital-surface-model-first-return-dsm-1m/wcs`, `.../lidar-composite-digital-surface-model-last-return-dsm-1m/wcs`
- EA tile search API (undocumented): `POST https://environment.data.gov.uk/backend/catalog/api/tiles/collections/survey/search` with a GeoJSON polygon; tiles from `https://environment.data.gov.uk/tiles/collections/survey/...`
- EIDC COGs: `https://catalogue.ceh.ac.uk/datastore/eidchub/34443359-64c0-4909-9f27-bb5d47f1153f/merged_engwal_{dtm,dsm}.tif`
- OS NGD API collections: `https://api.os.uk/features/ngd/ofa/v1/collections`
- OSTN15 grid: `https://cdn.proj.org/uk_os_OSTN15_NTv2_OSGBtoETRS.tif`

**Documentation and terms:**

- [LIDAR Composite DSM 1m, data.gov.uk (licence, attribution, endpoints)](https://www.data.gov.uk/dataset/cf3f1137-c12b-44a1-a835-e80fe4a60b92/lidar-composite-digital-surface-model-dsm-1m)
- [LIDAR Composite DTM 1m, Defra](https://environment.data.gov.uk/dataset/13787b9a-26a4-4775-8523-806d13af58fc)
- [National LIDAR Programme, data.gov.uk](https://data.gov.uk/dataset/f0db0249-f17b-4036-9e65-309148c97ce4/national-lidar-programme)
- [EA blog: LIDAR released as open data under OGL (2015)](https://environmentagency.blog.gov.uk/2015/09/18/laser-surveys-light-up-open-data/)
- [EA LIDAR Open Data FAQ](https://www.owenboswarva.com/opendata/EA/Environment_Agency_LIDAR_Open_Data_FAQ_v5.pdf)
- [EIDC merged England and Wales DTM/DSM record](https://catalogue.ceh.ac.uk/documents/34443359-64c0-4909-9f27-bb5d47f1153f) and [data.gov.uk listing](https://ckan.publishing.service.gov.uk/dataset/merged-lidar-based-digital-terrain-model-dtm-and-digital-surface-model-dsm-for-england-and-wale)
- [NERC-CEH dtm-analysis notebooks](https://github.com/NERC-CEH/dtm-analysis) and [Zenodo record](https://zenodo.org/records/21297015)
- [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/)
- [Google Map Tiles API policies](https://developers.google.com/maps/documentation/tile/policies) and [Photorealistic 3D Tiles FAQ](https://mapsplatform.google.com/resources/blog/commonly-asked-questions-about-our-recently-launched-photorealistic-3d-tiles/)
- [OS Terrain 5 product supply](https://docs.os.uk/os-downloads/height-and-imagery/os-terrain-5/os-terrain-5-overview/product-supply)
- [OS 3D Mesh beta overview](https://docs.os.uk/os-downloads/height-and-imagery/os-3d-mesh-beta-product/overview) and [product page](https://www.ordnancesurvey.co.uk/products/os-3d-mesh)
- [OS NGD Building Part feature type (heights)](https://docs.os.uk/more-than-maps/demonstrators/os-national-geographic-database/os-ngd-buildings/building-part-feature-type)
- [OS Data Hub plans](https://osdatahub.os.uk/plans) and [OS Data Hub overview](https://www.ordnancesurvey.co.uk/developers/os-data-hub)
- [OS OpenMap Local overview](https://docs.os.uk/os-downloads/products/maps-and-imagery-portfolio/os-openmap-local/os-openmap-local-overview) and [product page](https://ordnancesurvey.co.uk/business-government/products/open-map-local)
- [Talk-GB on OpenMap Local building generalisation](https://lists.openstreetmap.org/pipermail/talk-gb/2015-November/018060.html)
- [OS Maps API layers and styles](https://docs.os.uk/os-apis/accessing-os-apis/os-maps-api/layers-and-styles)
- [Bluesky DSM on UP42](https://up42.com/marketplace/data/archive/bluesky-dsm) and [Bluesky OS partner page](https://www.ordnancesurvey.co.uk/customers/businesses/find-a-business-partner/bluesky-international-limited)
- [NRW licence note on Getmapping/Bluesky data](https://metadata.naturalresources.wales/geonetwork/srv/api/records/EXT_DS121661)
- [Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM) and [FABDEM (Fathom)](https://www.fathom.global/?p=18211)
- [OSMF attribution guidelines](https://osmfoundation.org/wiki/Attribution) and [ODbL in the 3D topic](https://community.openstreetmap.org/t/odbl-in-the-3d-topic/62486)
- [Overpass API (usage guidance)](https://wiki.openstreetmap.org/wiki/Overpass_API) and [Overpass manual](https://dev.overpass-api.de/overpass-doc/en/preface/commons.html)
- [Overture buildings guide](https://docs.overturemaps.org/guides/buildings)
- [DataMapWales LIDAR catalogue](https://datamap.gov.wales/layers/inspire-nrw:NRW_LIDAR_ARCHIVE_TILE_CATALOGUE) and [NRW LIDAR metadata](https://metadata.naturalresources.wales/geonetwork/srv/api/records/NRW_DS116814?language=eng)
- [Scottish Remote Sensing Portal](https://remotesensingdata.gov.scot/about)
- [Bambu Lab A1 mini tech specs (store)](https://eu.store.bambulab.com/products/a1-mini%0A)
- [Bambu forum: overlapping parts priority](https://forum.bambulab.com/t/overlap-between-multiple-parts-in-a-single-object/122020) and [3MF structure notes](https://printago.io/blog/3mf-file-format)
