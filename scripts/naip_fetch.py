"""
Fetch NAIP imagery for a bounding box.

Exploratory script for evaluating NAIP as an imagery source (see the
geospatial team's imagery-source-selection ticket). Not wired into the
basemap_pipeline package yet -- once a source is confirmed, this logic
should move to src/basemap_pipeline/sources/naip.py and be called from
generate_basemap() in core.py.

Two approaches, both free and keyless (NAIP is U.S. public domain):

1. fetch_naip_exportimage() -- USGS ImageServer, good for quick single-tile
   pulls and manual testing. Returns one raster for your bbox at the pixel
   size you ask for.

2. search_naip_stac() -- Microsoft Planetary Computer STAC API, good for
   production use. Returns a list of cloud-optimized GeoTIFF (COG) scene
   URLs covering your bbox, which GDAL/Rasterio can read directly (even
   partially, without downloading the whole file) -- this is the shape
   the fetch/stitch pipeline will eventually want.

Usage:
    python naip_fetch.py
(runs the Port Jefferson, NY example bbox at the bottom of this file)

Requires: pip install requests
"""

import requests

USGS_IMAGE_SERVER = (
    "https://imagery.nationalmap.gov/arcgis/rest/services/"
    "USGSNAIPPlus/ImageServer/exportImage"
)

PLANETARY_COMPUTER_STAC = "https://planetarycomputer.microsoft.com/api/stac/v1"


def fetch_naip_exportimage(bbox, out_path, size=(1024, 1024), fmt="tiff"):
    """Download one NAIP raster covering `bbox` via the USGS ImageServer.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) in WGS84 degrees.
        out_path: where to save the image, e.g. "sample.tif".
        size: (width, height) in output pixels.
        fmt: "tiff" for a georeferenced GeoTIFF, or "jpgpng" for a quick
             visual-only preview (no coordinate info embedded).

    Returns:
        The output path on success.

    Raises:
        requests.HTTPError if the service returns an error.
        RuntimeError if the service returns JSON (an error payload)
        instead of image bytes -- this happens if a parameter is wrong.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    params = {
        "bbox": f"{min_lon},{min_lat},{max_lon},{max_lat}",
        "bboxSR": 4326,
        "size": f"{size[0]},{size[1]}",
        "imageSR": 4326,
        "format": fmt,
        "pixelType": "U8",
        "f": "image",
    }

    resp = requests.get(USGS_IMAGE_SERVER, params=params, timeout=60)
    resp.raise_for_status()

    content_type = resp.headers.get("Content-Type", "")
    if "json" in content_type:
        # The server reports errors as JSON even though we asked for f=image
        raise RuntimeError(f"ImageServer returned an error: {resp.text}")

    with open(out_path, "wb") as f:
        f.write(resp.content)

    return out_path


def search_naip_stac(bbox, limit=10, year=None):
    """Find NAIP scenes covering `bbox` via the Planetary Computer STAC API.

    Args:
        bbox: (min_lon, min_lat, max_lon, max_lat) in WGS84 degrees.
        limit: max number of scenes to return.
        year: optional 4-digit year to filter to, e.g. 2022. NAIP is
              collected on a roughly 2-3 year cycle and varies by state,
              so omit this to get whatever is actually available.

    Returns:
        A list of dicts: [{"id": ..., "datetime": ..., "cog_url": ...}, ...]
        `cog_url` points at a cloud-optimized GeoTIFF that GDAL/Rasterio
        can stream directly (see note at bottom of file).
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    search_body = {
        "collections": ["naip"],
        "bbox": [min_lon, min_lat, max_lon, max_lat],
        "limit": limit,
    }
    if year:
        search_body["datetime"] = f"{year}-01-01T00:00:00Z/{year}-12-31T23:59:59Z"

    resp = requests.post(f"{PLANETARY_COMPUTER_STAC}/search", json=search_body, timeout=30)
    resp.raise_for_status()
    features = resp.json().get("features", [])

    results = []
    for feature in features:
        assets = feature.get("assets", {})
        # The actual 4-band COG is usually under the "image" asset key
        cog_url = assets.get("image", {}).get("href")
        results.append(
            {
                "id": feature.get("id"),
                "datetime": feature.get("properties", {}).get("datetime"),
                "cog_url": cog_url,
            }
        )
    return results


if __name__ == "__main__":
    # Small bbox in Port Jefferson, NY -- same test location used for the
    # NOAA Digital Coast tile earlier in this ticket, for a fair comparison.
    port_jefferson_bbox = (-73.070, 40.945, -73.060, 40.953)

    print("Fetching NAIP image via USGS ImageServer...")
    out_file = fetch_naip_exportimage(
        bbox=port_jefferson_bbox,
        out_path="naip_port_jefferson.tif",
        size=(1024, 1024),
    )
    print(f"Saved: {out_file}")

    print("\nSearching Planetary Computer STAC for scenes over the same bbox...")
    scenes = search_naip_stac(port_jefferson_bbox, limit=3)
    for s in scenes:
        print(f"  {s['id']}  ({s['datetime']})")
        print(f"    {s['cog_url']}")

    # Note on reading the COG URLs from search_naip_stac():
    # Rasterio/GDAL can open them directly over HTTP without downloading
    # the whole file first, e.g.:
    #
    #   import rasterio
    #   with rasterio.open(scenes[0]["cog_url"]) as src:
    #       window = src.window(*port_jefferson_bbox)  # just the area you need
    #       data = src.read(window=window)
    #
    # This only pulls the bytes covering your bbox, not the full scene --
    # relevant for the fetch/stitch pipeline once this moves past testing.
