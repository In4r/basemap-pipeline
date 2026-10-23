# scripts/

Exploratory and one-off scripts — not part of the installed `basemap_pipeline`
package, not covered by CI lint/type-check/tests, and not imported by
anything in `src/`.

Use this folder for spikes like evaluating a candidate data source, trying
out an API, or a throwaway data-munging pass. Once something here proves
out and is ready to be real pipeline code, move/refactor it into `src/`
(with tests) rather than growing it in place.

## Current scripts

- **naip_fetch.py** — fetches/searches NAIP imagery for a bounding box via
  the USGS ImageServer and the Planetary Computer STAC API. Part of the
  imagery-source evaluation ticket; not yet wired into `generate_basemap()`.
- **noaa_fetch.py** — lists and downloads NOAA Digital Coast GeoTIFF tiles for a
  dataset folder and bounding box (CC0, no key). Written offline and **not yet
  run against the live site**; see its docstring for the assumptions to check.
  Offline tests are in `tests/test_noaa_fetch.py`. Needs `pip install requests pyproj`.
