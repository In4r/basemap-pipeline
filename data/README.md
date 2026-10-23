# data/

Imagery and annotations. The files themselves are stored with DVC, not git.
See [docs/storage.md](../docs/storage.md) for how to pull, add and version them.

Create these folders when you first have something to put in them, then run
`dvc add data/<folder>`:

```
raw/<source>/<year>/   source tiles, e.g. raw/noaa-dc/2026/ (optional to version)
chips/                 extracted GeoTIFF chips
annotations/           label masks, same file names as the chips
```

Only `README.md` and `PROVENANCE.md` are committed to git directly. Do not add
`.gitkeep` files inside DVC-tracked folders; DVC would treat them as data.
