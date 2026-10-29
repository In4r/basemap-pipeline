"""Core pipeline logic.

This module exposes the main entrypoint, `generate_basemap`, which takes a
bounding box and returns a geometry document (v0) of vectorized road features.
The imagery -> model -> vectorizer stages are not integrated yet, so until they
are, pass `use_mock=True` (hand-made vectors) or your own `polylines`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import NamedTuple


class BBox(NamedTuple):
    """A geographic bounding box in WGS84 decimal degrees."""

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def validate(self) -> None:
        if not (-180.0 <= self.min_lon < self.max_lon <= 180.0):
            raise ValueError(
                f"Invalid longitude range: min_lon={self.min_lon}, max_lon={self.max_lon}"
            )
        if not (-90.0 <= self.min_lat < self.max_lat <= 90.0):
            raise ValueError(
                f"Invalid latitude range: min_lat={self.min_lat}, max_lat={self.max_lat}"
            )


DEFAULT_EPSG = 2263  # NAD83 / New York Long Island (ftUS); pick the state plane zone for your bbox


@dataclass
class BasemapResult:
    """Result of `generate_basemap`.

    `document` is the geometry document (a JSON-serializable dict, v0 schema).
    `output_path` is set when a document was written to disk.
    """

    bbox: BBox
    output_path: str | None = None
    metadata: dict | None = None
    document: dict | None = None


def generate_basemap(
    bbox: tuple[float, float, float, float] | BBox,
    *,
    polylines: list | None = None,
    use_mock: bool = False,
    epsg: int = DEFAULT_EPSG,
    out_dir: str | None = None,
    min_full_confidence_length_ft: float | None = None,
) -> BasemapResult:
    """Generate a geometry document for the given bounding box.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) as a 4-tuple or `BBox`, WGS84.
        polylines: vectorized features (`geometry_document.Polyline`) already in
            the local projected CRS. This is where the vectorizer's output plugs in.
        use_mock: use hand-made vectors instead (marked `generator.mock = true`).
        epsg: EPSG code of the local projected CRS; must be in US survey feet.
        out_dir: if set, also write the document there (e.g. `data/outputs/geometry`).
        min_full_confidence_length_ft: override the confidence length scale.

    Raises:
        ValueError: invalid bbox, a CRS that is not US survey feet, or output that
            fails schema validation.
        NotImplementedError: no `polylines` given and `use_mock` is False (the
            imagery -> model -> vectorizer stages are not wired in yet).
    """
    from pyproj import CRS

    from basemap_pipeline import geometry_document as gd
    from basemap_pipeline.mock_vectors import mock_polylines
    from basemap_pipeline.validate import validate_document

    if not isinstance(bbox, BBox):
        bbox = BBox(*bbox)
    bbox.validate()

    crs = CRS.from_epsg(epsg)
    if "us survey foot" not in crs.axis_info[0].unit_name.lower():
        raise ValueError(f"EPSG:{epsg} is in {crs.axis_info[0].unit_name!r}; need US survey feet")

    is_mock = polylines is None
    if polylines is None:
        if not use_mock:
            raise NotImplementedError(
                "imagery -> model -> vectorizer is not wired in yet; "
                "pass polylines=... or use_mock=True"
            )
        polylines = mock_polylines(bbox, epsg)

    length_scale = (
        gd.DEFAULT_MIN_FULL_CONFIDENCE_LENGTH_FT
        if min_full_confidence_length_ft is None
        else min_full_confidence_length_ft
    )
    document = gd.build_document(
        bbox,
        polylines,
        epsg=epsg,
        crs_name=crs.name,
        mock=is_mock,
        min_full_confidence_length_ft=length_scale,
    )
    problems = validate_document(document)
    if problems:
        raise ValueError("emitted document failed schema validation: " + "; ".join(problems))

    path = gd.write_document(document, out_dir) if out_dir else None
    return BasemapResult(
        bbox=bbox,
        output_path=str(path) if path else None,
        metadata={"run_id": document["run_id"], "n_features": len(document["features"])},
        document=document,
    )
