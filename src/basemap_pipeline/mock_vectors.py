"""Hand-made vectors for developing the emitter before the real vectorizer lands.

These are NOT model output. Documents built from them are marked `generator.mock = true`.
Shapes are laid out inside the bbox so a test run produces plausible-looking geometry.
"""

from __future__ import annotations

from pyproj import Transformer

from basemap_pipeline.core import BBox
from basemap_pipeline.geometry_document import Polyline


def mock_polylines(bbox: BBox, epsg: int) -> list[Polyline]:
    """A lane line (3 dashes), a crosswalk edge, two curbs and a median, in CRS `epsg`."""
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    x0, y0 = tr.transform(bbox.min_lon, bbox.min_lat)
    x1, y1 = tr.transform(bbox.max_lon, bbox.max_lat)
    w, h = x1 - x0, y1 - y0

    def at(fx: float, fy: float) -> tuple[float, float]:
        return (round(x0 + fx * w, 3), round(y0 + fy * h, 3))

    return [
        Polyline("lane_line", [at(0.05, 0.50), at(0.25, 0.50)], 0.94),
        Polyline("lane_line", [at(0.32, 0.50), at(0.52, 0.50)], 0.88),
        Polyline("lane_line", [at(0.59, 0.50), at(0.79, 0.50)], 0.61),
        Polyline("crosswalk_edge", [at(0.88, 0.40), at(0.88, 0.60)], 0.83),
        Polyline("curb", [at(0.05, 0.38), at(0.50, 0.385), at(0.95, 0.38)], 0.91),
        Polyline("curb", [at(0.05, 0.62), at(0.50, 0.615), at(0.95, 0.62)], 0.47),
        Polyline("median", [at(0.10, 0.50), at(0.11, 0.50)], 0.70),
    ]
