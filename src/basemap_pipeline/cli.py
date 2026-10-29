"""Command-line entrypoint for the basemap pipeline."""

from __future__ import annotations

import argparse
import sys

from basemap_pipeline.core import DEFAULT_EPSG, generate_basemap


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="generate-basemap",
        description="Generate a basemap for a given bounding box.",
    )
    parser.add_argument("min_lon", type=float, help="Minimum longitude")
    parser.add_argument("min_lat", type=float, help="Minimum latitude")
    parser.add_argument("max_lon", type=float, help="Maximum longitude")
    parser.add_argument("max_lat", type=float, help="Maximum latitude")
    parser.add_argument("--mock", action="store_true", help="use hand-made vectors (dev only)")
    parser.add_argument("--epsg", type=int, default=DEFAULT_EPSG, help="local CRS, US survey feet")
    parser.add_argument("--out-dir", help="write the geometry document here")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    bbox = (args.min_lon, args.min_lat, args.max_lon, args.max_lat)
    try:
        result = generate_basemap(bbox, use_mock=args.mock, epsg=args.epsg, out_dir=args.out_dir)
        print(result.output_path or f"{result.metadata} (not written; pass --out-dir)")
        return 0
    except NotImplementedError as exc:
        print(f"Not yet implemented: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
