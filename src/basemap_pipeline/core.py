"""Core pipeline logic.

This module exposes the main entrypoint, `generate_basemap`, which will
eventually take a bounding box and produce a rendered basemap (tiles,
a raster, a vector layer, etc.). For now it is a stub: the signature,
input validation, and return contract are defined, but the actual
generation logic is not yet implemented.
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


@dataclass
class BasemapResult:
    """Placeholder result type for a generated basemap.

    Once implemented, this might hold a file path, an in-memory raster,
    a tile manifest, or similar — adjust to fit the real pipeline output.
    """

    bbox: BBox
    output_path: str | None = None
    metadata: dict | None = None


def generate_basemap(bbox: tuple[float, float, float, float] | BBox) -> BasemapResult:
    """Generate a basemap for the given bounding box.

    Args:
        bbox: A bounding box as (min_lon, min_lat, max_lon, max_lat), either
            a plain 4-tuple or a `BBox` instance.

    Returns:
        A `BasemapResult` describing the generated basemap.

    Raises:
        ValueError: If the bounding box is invalid.
        NotImplementedError: Always, until the pipeline is implemented.
    """
    if not isinstance(bbox, BBox):
        bbox = BBox(*bbox)
    bbox.validate()

    # TODO: implement the actual pipeline, e.g.:
    #   1. Fetch source imagery/vector data covering `bbox`
    #      (see scripts/naip_fetch.py for an evaluation of NAIP as a source)
    #   2. Reproject / mosaic / clip to `bbox`
    #   3. Render or tile the result
    #   4. Write output and return its location + metadata
    raise NotImplementedError("generate_basemap is a stub — pipeline not yet implemented")
