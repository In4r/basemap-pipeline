# basemap-pipeline

Pipeline for generating basemap layers from a bounding box. Currently a
scaffold: project structure, containerization, and CI are wired up, but
`generate_basemap` emits and validates a geometry document, but the
imagery -> model -> vectorizer stages are not wired in yet (use `--mock`).

## Layout

```
basemap-pipeline/
├── src/basemap_pipeline/
│   ├── __init__.py       # package exports
│   ├── core.py             # BBox type + generate_basemap() -> geometry document
│   ├── geometry_document.py # v0 document builder + confidence
│   ├── validate.py          # schema validation (`validate-geometry`)
│   ├── mock_vectors.py      # hand-made vectors until the vectorizer lands
│   ├── schema/              # geometry_document_v0.schema.json
│   └── cli.py               # `generate-basemap` CLI entrypoint
├── scripts/                  # exploratory/one-off scripts, not part of the package
│   ├── naip_fetch.py
│   ├── noaa_fetch.py
│   ├── publish_outputs.sh
│   └── storage_smoke_test.sh
├── data/                     # imagery + annotations, versioned with DVC (see docs/storage.md)
├── models/                   # checkpoints, versioned with DVC
├── docs/
│   └── storage.md            # how to push/pull versioned imagery and artifacts
├── .dvc/                     # DVC config (remote = R2/S3 bucket)
├── tests/
│   └── test_core.py
├── Dockerfile
├── .dockerignore
├── pyproject.toml
└── .github/workflows/ci.yml
```

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Usage

```python
from basemap_pipeline import generate_basemap

generate_basemap((-73.070, 40.945, -73.060, 40.953), use_mock=True).document
```

Or via CLI:

```bash
generate-basemap --mock --out-dir data/outputs/geometry -73.070 40.945 -73.060 40.953
validate-geometry data/outputs/geometry/*.json
```

See [docs/geometry-document.md](docs/geometry-document.md) for the document format,
confidence, and how to fetch emitted documents from storage.

## Data and model storage

Imagery, annotations and model checkpoints are versioned with DVC and stored in
a bucket. Start with [docs/storage.md](docs/storage.md).

```bash
pip install -e ".[storage]"
dvc pull
```

## Docker

```bash
docker build -t basemap-pipeline .
docker run --rm basemap-pipeline -122.5 37.7 -122.3 37.9
```

## Next steps

- Implement the real pipeline in `core.py` (data source, reprojection,
  rendering/tiling, output writing).
- Add geospatial dependencies (e.g. `rasterio`, `shapely`, `geopandas`)
  to `pyproject.toml` and system deps (`gdal-bin`) to the `Dockerfile`.
- Expand `BasemapResult` to reflect the real output shape.
- Once an imagery source is confirmed (see `scripts/naip_fetch.py`),
  move the fetch logic into `src/basemap_pipeline/sources/` and wire it
  into `generate_basemap()`.
