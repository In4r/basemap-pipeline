# basemap-pipeline

Pipeline for generating basemap layers from a bounding box. Currently a
scaffold: project structure, containerization, and CI are wired up, but
the actual generation logic in `generate_basemap` is a stub.

## Layout

```
basemap-pipeline/
├── src/basemap_pipeline/
│   ├── __init__.py       # package exports
│   ├── core.py            # BBox type + generate_basemap() stub
│   └── cli.py              # `generate-basemap` CLI entrypoint
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

generate_basemap((-122.5, 37.7, -122.3, 37.9))  # raises NotImplementedError for now
```

Or via CLI:

```bash
generate-basemap -122.5 37.7 -122.3 37.9
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
