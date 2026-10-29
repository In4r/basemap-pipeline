# Geometry document emitter (GEO-W4-2)

`generate_basemap(bbox, ...)` returns a **geometry document**: vectorized road
features in a local projected CRS (U.S. survey feet), each with a confidence.
Every document is checked against a JSON Schema before it is returned or written,
and CI fails the build if emitted output is malformed.

## Read this first: the schema is my assumption

I did not have the team's geometry-document v0 spec when I built this. The schema
in `src/basemap_pipeline/schema/geometry_document_v0.schema.json` is **my guess**
from the W4 ticket (object types, CRS, confidence fields). Before relying on it,
compare it with the real spec and edit that one JSON file. Everything else reads
it from there; the document builder in `geometry_document.py` is the only other
place that needs to follow any field changes.

Things most likely to differ from the real spec: feature class names, the shape of
`confidence`, the `crs` block, and whether features are GeoJSON-style.

## What it emits

```json
{
  "schema_version": "0",
  "run_id": "20261029T065004Z-92c2e610",
  "generated_at": "2026-10-29T06:50:04+00:00",
  "generator": {"name": "basemap-pipeline", "version": "0.1.0", "mock": true},
  "bbox": {"min_lon": -73.07, "min_lat": 40.945, "max_lon": -73.06, "max_lat": 40.953},
  "crs": {"epsg": 2263, "name": "NAD83 / New York Long Island (ftUS)", "units": "us-survey-foot"},
  "confidence_method": {"name": "mean_probability_x_length_v0", "min_full_confidence_length_ft": 30.0},
  "features": [
    {"id": "lane_line-0001", "class": "lane_line", "length_ft": 546.2,
     "geometry": {"type": "LineString", "coordinates": [[x, y], [x, y]]},
     "confidence": {"score": 0.94, "mean_mask_probability": 0.94, "length_ft": 546.2}}
  ]
}
```

Classes: `lane_line`, `crosswalk_edge`, `curb`, `median` (from Sriya's ticket).
Coordinates are `[x, y]` in the CRS given by `crs.epsg`. `generator.mock` is `true`
when the vectors were hand-made, so mock output can never be mistaken for real.

## Using it

```python
from basemap_pipeline import generate_basemap
from basemap_pipeline.geometry_document import Polyline

# Sriya's vectorizer output plugs in here: polylines already in the local CRS (ftUS)
lines = [Polyline("curb", [(x1, y1), (x2, y2)], mean_mask_probability=0.9)]
result = generate_basemap(bbox, polylines=lines, epsg=2263, out_dir="data/outputs/geometry")
result.document      # the dict
result.output_path   # the file, if out_dir was given
```

- Until the vectorizer lands, `use_mock=True` (CLI: `--mock`) uses hand-made vectors.
  With neither `polylines` nor `use_mock`, it raises `NotImplementedError` rather than
  silently emitting nothing.
- `epsg` defaults to 2263 (Long Island, for the Port Jefferson test bbox). Pick the
  State Plane zone in US survey feet for your area. A CRS in metres is rejected.
  This does not call the Week 2 coordinate module; vectors must already be in the
  local CRS when they arrive.
- If the vectorizer gives you a probability raster rather than a per-line number,
  `geometry_document.mean_mask_probability(prob, origin_xy, pixel_size_ft, coords)`
  samples it along a line (north-up raster assumed).

## How confidence is computed

Basic version, as the ticket asks. For each feature:

```
score = mean_mask_probability x min(1, length_ft / 30)
```

- `mean_mask_probability`: mean of the model's class probability along the line, 0 to 1.
- `length_ft`: polyline length in feet.
- 30 ft is `min_full_confidence_length_ft`. Features at least that long keep their
  mask probability; shorter fragments (despiked leftovers, single dashes) scale down
  proportionally. The 30 ft value is **my choice, not tuned**; change it per call
  with `min_full_confidence_length_ft=` and it is recorded in the document.

All three numbers are stored so later versions can change the formula without
losing inputs. Prior-agreement scoring is deferred to Week 5, per the ticket.

## Validation and CI

```bash
validate-geometry data/outputs/geometry/*.json    # exit code 1 if anything fails
```

Beyond the JSON Schema it checks: bbox ordering, unique feature ids, finite
coordinates, and that `length_ft` matches the geometry within 1%. CI generates a
mock document and validates it, and `tests/test_geometry_document.py` confirms
nine kinds of malformed documents are rejected.

## Storing and fetching emitted documents

Documents live in `data/outputs/geometry/`, versioned with DVC like the rest of
`data/` (see `docs/storage.md` for one-time credential setup).

**Publish** (validates first, so a bad file never reaches the bucket):

```bash
generate-basemap --out-dir data/outputs/geometry ...   # or your own call
bash scripts/publish_outputs.sh
git add data/outputs.dvc data/.gitignore && git commit -m "outputs: <what changed>"
git tag outputs-v1        # optional, for a version worth returning to
git push --follow-tags
```

**Fetch** (anyone on the team):

```bash
git pull
dvc pull data/outputs.dvc
ls data/outputs/geometry/
```

**Fetch an older set:** `git checkout outputs-v1 -- data/outputs.dvc && dvc pull data/outputs.dvc`.

## Status

| Piece | State |
|---|---|
| Emitter, confidence, schema validation, CI step | Done; 30 tests pass; ruff and mypy clean |
| Publish and fetch through DVC | Tested against a local remote (publish, then fresh clone and `dvc pull`) |
| Cloud bucket | Not created yet (same blocker as `docs/storage.md`) |
| Match to the real v0 spec | **Not checked: spec not available to me** |
| Real vectors | Not integrated; mock only until Sriya's module lands |
