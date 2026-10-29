"""Build and write geometry documents (v0).

A geometry document holds vectorized road features in a local projected CRS
(U.S. survey feet), each with a basic confidence. See docs/geometry-document.md.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise
from pathlib import Path
from typing import Any

import numpy as np

import basemap_pipeline
from basemap_pipeline.core import BBox

SCHEMA_VERSION = "0"
CONFIDENCE_METHOD = "mean_probability_x_length_v0"
DEFAULT_MIN_FULL_CONFIDENCE_LENGTH_FT = 30.0
FEATURE_CLASSES = ("lane_line", "crosswalk_edge", "curb", "median")

Coord = tuple[float, float]


@dataclass
class Polyline:
    """One vectorized feature, in the local projected CRS (US survey feet)."""

    cls: str
    coords: list[Coord]
    mean_mask_probability: float


def line_length(coords: Sequence[Coord]) -> float:
    return sum(math.dist(a, b) for a, b in pairwise(coords))


def confidence_score(
    mean_probability: float,
    length_ft: float,
    min_full_confidence_length_ft: float = DEFAULT_MIN_FULL_CONFIDENCE_LENGTH_FT,
) -> float:
    """score = mean mask probability x min(1, length / min_full_confidence_length_ft).

    Short fragments (despiked leftovers, dash pieces) are scaled down; features at
    least `min_full_confidence_length_ft` long keep their mask probability.
    """
    if min_full_confidence_length_ft <= 0:
        raise ValueError("min_full_confidence_length_ft must be > 0")
    p = min(1.0, max(0.0, mean_probability))
    return round(p * min(1.0, length_ft / min_full_confidence_length_ft), 4)


def mean_mask_probability(
    prob: np.ndarray,
    origin_xy: Coord,
    pixel_size_ft: float,
    coords: Sequence[Coord],
) -> float:
    """Mean of a class probability raster sampled along a polyline.

    Assumes a north-up raster: `origin_xy` is the (x, y) of the top-left corner in
    the same CRS as `coords`, and rows increase southward. Samples every half pixel;
    samples outside the raster are ignored.
    """
    step = pixel_size_ft / 2.0
    samples: list[float] = []
    height, width = prob.shape
    for (x0, y0), (x1, y1) in pairwise(coords):
        n = max(1, int(math.dist((x0, y0), (x1, y1)) / step))
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            col = int((x - origin_xy[0]) // pixel_size_ft)
            row = int((origin_xy[1] - y) // pixel_size_ft)
            if 0 <= row < height and 0 <= col < width:
                samples.append(float(prob[row, col]))
    if not samples:
        raise ValueError("polyline lies entirely outside the probability raster")
    return float(np.mean(samples))


def build_document(
    bbox: BBox,
    polylines: Sequence[Polyline],
    *,
    epsg: int,
    crs_name: str,
    mock: bool,
    min_full_confidence_length_ft: float = DEFAULT_MIN_FULL_CONFIDENCE_LENGTH_FT,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(UTC)
    digest = hashlib.sha1(
        json.dumps([list(bbox), [(p.cls, p.coords) for p in polylines]]).encode()
    ).hexdigest()[:8]
    features = []
    for i, poly in enumerate(polylines, start=1):
        if poly.cls not in FEATURE_CLASSES:
            raise ValueError(f"unknown feature class {poly.cls!r}; expected {FEATURE_CLASSES}")
        length = round(line_length(poly.coords), 3)
        features.append(
            {
                "id": f"{poly.cls}-{i:04d}",
                "class": poly.cls,
                "geometry": {"type": "LineString", "coordinates": [list(c) for c in poly.coords]},
                "length_ft": length,
                "confidence": {
                    "score": confidence_score(
                        poly.mean_mask_probability, length, min_full_confidence_length_ft
                    ),
                    "mean_mask_probability": round(poly.mean_mask_probability, 4),
                    "length_ft": length,
                },
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": f"{now:%Y%m%dT%H%M%SZ}-{digest}",
        "generated_at": now.isoformat(timespec="seconds"),
        "generator": {"name": "basemap-pipeline", "version": basemap_pipeline.__version__, "mock": mock},
        "bbox": bbox._asdict(),
        "crs": {"epsg": epsg, "name": crs_name, "units": "us-survey-foot"},
        "confidence_method": {
            "name": CONFIDENCE_METHOD,
            "min_full_confidence_length_ft": min_full_confidence_length_ft,
        },
        "features": features,
    }


def write_document(document: dict[str, Any], out_dir: str | Path) -> Path:
    """Write `<out_dir>/geometry_<run_id>.json` and return the path."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"geometry_{document['run_id']}.json"
    path.write_text(json.dumps(document, indent=2) + "\n")
    return path
