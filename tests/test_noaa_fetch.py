"""Offline tests for scripts/noaa_fetch.py (no network)."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "noaa_fetch", Path(__file__).parent.parent / "scripts" / "noaa_fetch.py"
)
noaa = importlib.util.module_from_spec(spec)
spec.loader.exec_module(noaa)

BASE = "https://example.test/digitalcoast/DS/"
HTML = """
<html><body>
<a href="651000e4536000n.tif">a</a>
<a href="/digitalcoast/DS/652000e4536000n.tif">b</a>
<a href="651000e4536000n.tif">dup</a>
<a href="notes.txt">c</a>
<a href="index.html">d</a>
<a href="710000e4600000n.tif?x=1">far</a>
</body></html>
"""


def test_parse_tile_links_dedupes_and_filters():
    urls = noaa.parse_tile_links(HTML, BASE)
    assert urls == [
        BASE + "651000e4536000n.tif",
        "https://example.test/digitalcoast/DS/652000e4536000n.tif",
        BASE + "710000e4600000n.tif?x=1",
    ]


def test_tile_origin():
    assert noaa.tile_origin(BASE + "651000e4536000n.tif") == (651000, 4536000)
    assert noaa.tile_origin(BASE + "readme.tif") is None


def test_utm_zone_for_long_island_is_18n():
    assert noaa.utm_epsg_for(-73.07, 40.95) == 32618


def test_bbox_selects_overlapping_tiles():
    pytest.importorskip("pyproj")
    urls = noaa.parse_tile_links(HTML, BASE)
    # UTM box inside the first tile only
    got = noaa.tiles_in_bbox(urls, (651100, 4536100, 651200, 4536200))
    assert got == [BASE + "651000e4536000n.tif"]
    # box straddling the first two tiles
    got = noaa.tiles_in_bbox(urls, (651900, 4536100, 652100, 4536200))
    assert len(got) == 2


def test_bbox_to_utm_is_in_expected_range():
    pytest.importorskip("pyproj")
    min_e, min_n, max_e, max_n = noaa.bbox_to_utm((-73.07, 40.945, -73.06, 40.953))
    assert 660000 < min_e < max_e < 665000
    assert 4534000 < min_n < max_n < 4536500


def test_download_requires_selector(capsys):
    with pytest.raises(SystemExit):
        noaa.main(["download", "DS"])
