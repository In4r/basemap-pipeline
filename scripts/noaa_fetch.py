"""
Fetch NOAA Digital Coast imagery tiles.

Exploratory script, same status as naip_fetch.py: not part of the installed
package. If it proves out, move the logic to src/basemap_pipeline/sources/noaa.py.

Digital Coast imagery datasets are folders of GeoTIFF tiles on public Azure blob
storage, with an index.html that lists them. No account or key is needed, and
the data is CC0. A dataset looks like:

    https://coastalimagery.blob.core.windows.net/digitalcoast/<DATASET>/index.html
    e.g. PortJeffersonNY_RGBN_2026_14587

Tile file names encode the tile's lower-left corner in UTM metres, e.g.
`651000e4536000n.tif` (easting 651000, northing 4536000).

NOT TESTED AGAINST THE LIVE SITE. It was written in a sandbox that cannot reach
the host, so the index parsing and bbox maths are only checked offline
(tests/test_noaa_fetch.py). Assumptions to confirm on first real run:
  1. index.html contains links to the .tif tiles (we parse every href ending .tif)
  2. tile names look like <easting>e<northing>n.tif (see TILE_RE)
  3. tiles are TILE_SIZE_M metres square (default 1000; override with --tile-size)
  4. the dataset's CRS is a UTM zone (zone is chosen from the bbox centre)
Use `list` first, check the numbers look right, then `download`.

Usage:
    python noaa_fetch.py list     DATASET --bbox MIN_LON MIN_LAT MAX_LON MAX_LAT
    python noaa_fetch.py download DATASET --bbox ... --out data/raw/noaa-dc/2026 [--max-tiles 5]
    python noaa_fetch.py download DATASET --match 651000e4536000n --out ...

Requires: pip install requests pyproj
After downloading, add a row to data/PROVENANCE.md.
"""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

BASE_URL = "https://coastalimagery.blob.core.windows.net/digitalcoast/"
TILE_RE = re.compile(r"(\d+)e(\d+)n\.tif$", re.IGNORECASE)
DEFAULT_TILE_SIZE_M = 1000


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for key, value in attrs:
                if key == "href" and value:
                    self.hrefs.append(value)


def dataset_url(dataset):
    return f"{BASE_URL}{dataset.strip('/')}/"


def parse_tile_links(index_html, base_url):
    """Return absolute URLs of every .tif linked from an index page."""
    parser = _LinkParser()
    parser.feed(index_html)
    seen, urls = set(), []
    for href in parser.hrefs:
        if href.lower().split("?")[0].endswith(".tif"):
            url = urljoin(base_url, href)
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def tile_origin(url):
    """(easting, northing) of the tile's lower-left corner, or None if the name does not match."""
    m = TILE_RE.search(url.split("?")[0])
    return (int(m.group(1)), int(m.group(2))) if m else None


def utm_epsg_for(lon, lat):
    zone = int((lon + 180) // 6) + 1
    return (32600 if lat >= 0 else 32700) + zone


def bbox_to_utm(bbox):
    """Convert a WGS84 bbox to a UTM bbox (min_e, min_n, max_e, max_n), zone from its centre."""
    from pyproj import Transformer

    min_lon, min_lat, max_lon, max_lat = bbox
    epsg = utm_epsg_for((min_lon + max_lon) / 2, (min_lat + max_lat) / 2)
    tr = Transformer.from_crs(4326, epsg, always_xy=True)
    xs, ys = zip(*[tr.transform(lon, lat) for lon in (min_lon, max_lon) for lat in (min_lat, max_lat)])
    return min(xs), min(ys), max(xs), max(ys)


def tiles_in_bbox(urls, utm_bbox, tile_size=DEFAULT_TILE_SIZE_M):
    """Keep the tiles whose square footprint overlaps the UTM bbox."""
    min_e, min_n, max_e, max_n = utm_bbox
    keep = []
    for url in urls:
        origin = tile_origin(url)
        if origin is None:
            continue
        e, n = origin
        if e < max_e and e + tile_size > min_e and n < max_n and n + tile_size > min_n:
            keep.append(url)
    return keep


def list_tiles(dataset):
    import requests

    base = dataset_url(dataset)
    resp = requests.get(base + "index.html", timeout=60)
    resp.raise_for_status()
    return parse_tile_links(resp.text, base)


def download(url, out_dir):
    import requests

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / url.split("?")[0].rsplit("/", 1)[-1]
    if out_path.exists():
        print(f"  skip (exists): {out_path}")
        return out_path
    tmp = out_path.with_suffix(".part")
    with requests.get(url, stream=True, timeout=120) as resp:
        resp.raise_for_status()
        with open(tmp, "wb") as f:
            f.writelines(resp.iter_content(1 << 20))
    tmp.rename(out_path)
    print(f"  saved: {out_path} ({out_path.stat().st_size / 1e6:.1f} MB)")
    return out_path


def select(args):
    urls = list_tiles(args.dataset)
    print(f"{len(urls)} tiles listed in {args.dataset}")
    if args.match:
        urls = [u for u in urls if args.match in u]
    if args.bbox:
        urls = tiles_in_bbox(urls, bbox_to_utm(args.bbox), args.tile_size)
    return urls


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    p.add_argument("command", choices=["list", "download"])
    p.add_argument("dataset", help="folder name, e.g. PortJeffersonNY_RGBN_2026_14587")
    p.add_argument("--bbox", nargs=4, type=float, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"))
    p.add_argument("--match", help="only tiles whose URL contains this text")
    p.add_argument("--tile-size", type=int, default=DEFAULT_TILE_SIZE_M, help="tile edge in metres")
    p.add_argument("--out", default="data/raw/noaa-dc", help="download folder")
    p.add_argument("--max-tiles", type=int, default=5, help="safety cap for download")
    args = p.parse_args(argv)

    if not args.bbox and not args.match and args.command == "download":
        p.error("download needs --bbox or --match so you do not pull the whole dataset")

    urls = select(args)
    print(f"{len(urls)} tiles selected")
    if args.command == "list":
        for u in urls[:50]:
            print(" ", u)
        if len(urls) > 50:
            print(f"  ... and {len(urls) - 50} more")
        return 0

    if len(urls) > args.max_tiles:
        print(f"Refusing: {len(urls)} tiles > --max-tiles {args.max_tiles}. Narrow the bbox or raise the cap.")
        return 1
    for u in urls:
        download(u, args.out)
    print("Now add a row to data/PROVENANCE.md (dataset name, year, bbox, tile IDs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
