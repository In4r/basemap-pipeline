"""Validate geometry documents against the v0 schema (plus consistency checks).

    validate-geometry path/to/geometry_*.json [more.json ...]

Exits non-zero if any document is malformed, so CI fails the build.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from importlib import resources
from itertools import pairwise
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

LENGTH_TOLERANCE = 0.01  # stored length_ft may differ from the geometry by 1%


def load_schema() -> dict[str, Any]:
    text = resources.files("basemap_pipeline").joinpath(
        "schema/geometry_document_v0.schema.json"
    ).read_text()
    schema: dict[str, Any] = json.loads(text)
    return schema


def validate_document(document: Any) -> list[str]:
    """Return a list of problems; an empty list means the document is valid."""
    validator = Draft202012Validator(load_schema())
    problems = [
        f"{'/'.join(str(p) for p in err.absolute_path) or '<root>'}: {err.message}"
        for err in sorted(validator.iter_errors(document), key=lambda e: list(e.absolute_path))
    ]
    if problems:
        return problems  # structure is wrong; skip the deeper checks

    bbox = document["bbox"]
    if not (bbox["min_lon"] < bbox["max_lon"] and bbox["min_lat"] < bbox["max_lat"]):
        problems.append("bbox: min must be less than max")
    seen: set[str] = set()
    for feat in document["features"]:
        fid = feat["id"]
        if fid in seen:
            problems.append(f"features/{fid}: duplicate id")
        seen.add(fid)
        coords = feat["geometry"]["coordinates"]
        if any(not math.isfinite(v) for c in coords for v in c):
            problems.append(f"features/{fid}: non-finite coordinate")
            continue
        actual = sum(math.dist(a, b) for a, b in pairwise(coords))
        if abs(actual - feat["length_ft"]) > LENGTH_TOLERANCE * max(actual, 1e-9):
            problems.append(
                f"features/{fid}: length_ft {feat['length_ft']} does not match geometry ({actual:.3f})"
            )
        if feat["confidence"]["length_ft"] != feat["length_ft"]:
            problems.append(f"features/{fid}: confidence.length_ft differs from length_ft")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="validate-geometry", description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)
    failed = False
    for path in args.files:
        try:
            problems = validate_document(json.loads(path.read_text()))
        except (OSError, json.JSONDecodeError) as exc:
            problems = [f"cannot read: {exc}"]
        if problems:
            failed = True
            print(f"FAIL {path}")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok   {path}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
