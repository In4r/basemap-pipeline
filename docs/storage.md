# Storage and versioning (GEO-W3-5)

How CloudTCP stores and versions imagery, annotations and model checkpoints.

**Short version:** large files live in a private S3-compatible bucket. Git stores
only small pointer files (`*.dvc`) that say which version of the data a commit
uses. [DVC](https://dvc.org) connects the two. Checking out a git commit or tag
and running `dvc pull` gives you exactly the data and model from that moment.

| Thing | Where it lives |
|---|---|
| Code, `*.dvc` pointer files, docs | Git (GitHub) |
| Imagery chips, annotation masks, checkpoints | Bucket, via DVC |
| Credentials | Your machine only (`.dvc/config.local`, never committed) |

## Status

| Piece | State |
|---|---|
| DVC config, folder layout, conventions, this doc | Done, in the repo |
| Push, pull and old-version restore | Tested end to end against a local remote (`scripts/storage_smoke_test.sh`) |
| Cloud bucket | **Not created yet.** Needs one person with a Cloudflare (or AWS) account. See "One-time admin setup" |
| Cloud remote (R2/S3) | **Untested.** The repo points at placeholder names until the bucket exists |

## Why DVC on Cloudflare R2

- **DVC** versions big files with git semantics (commit, tag, checkout), works with
  any S3-compatible bucket, and adds no server for us to run.
- **Cloudflare R2** is the recommended bucket because it has **no egress fee**, and
  egress is the cost that grows when teammates and CI repeatedly pull imagery and
  checkpoints. AWS S3 or GCS work with the same setup by changing the remote URL.
- Alternatives considered: plain bucket with object versioning (no link to git
  commits, so you cannot say "the data this model was trained on"); Git LFS
  (per-GB bandwidth quotas, awkward for directories of chips).

## Folder layout

```
data/
  raw/<source>/<year>/     source tiles, e.g. raw/noaa-dc/2026/  (optional to version)
  chips/                   extracted GeoTIFF chips
  annotations/             label masks, same file names as the chips
  PROVENANCE.md            where each raw pull came from (kept in git)
models/
  checkpoints/<arch>/<run-id>/   model.pt + metrics.json
```

Each of `data/raw`, `data/chips`, `data/annotations` and `models/checkpoints` is
tracked by DVC as one unit (`dvc add <dir>` creates `<dir>.dvc`). Train/val splits
and augmented data are **regenerable from the pipeline, so do not version them**
unless a split is frozen for a reported result.

## One-time setup (every teammate)

```bash
pip install -e ".[storage]"          # installs dvc[s3]
git pull                             # gets .dvc/config and the *.dvc files
```

Add your credentials locally. `--local` writes to `.dvc/config.local`, which is
git-ignored:

```bash
dvc remote modify --local storage access_key_id     <KEY_ID>
dvc remote modify --local storage secret_access_key <SECRET>
```

Get the key pair from the bucket admin. Never put keys in `.dvc/config`.

## Everyday commands

**Pull the data for the commit you have checked out**

```bash
git pull
dvc pull
```

**Add or change data, then share it**

```bash
dvc add data/chips                    # re-hash the folder, update data/chips.dvc
git add data/chips.dvc data/.gitignore
git commit -m "chips: add 40 arterial chips"
dvc push                              # upload the new files to the bucket
git push                              # share the pointer file
```

Push to the bucket **before** `git push`. A pointer file whose data is not in the
bucket breaks everyone's `dvc pull`.

**Save a checkpoint**

```bash
mkdir -p models/checkpoints/segformer-b2/run-007
cp model.pt metrics.json models/checkpoints/segformer-b2/run-007/
dvc add models/checkpoints
git add models/checkpoints.dvc models/.gitignore
git commit -m "model: segformer-b2 run-007 (see metrics.json)"
dvc push && git push
```

## Naming and versions

Mark every version someone may need to return to with a git tag:

| Tag | Meaning | Example |
|---|---|---|
| `data-vN` | A dataset state used for training or reporting | `data-v3` |
| `model-<arch>-vN` | A checkpoint worth keeping | `model-segformer-b2-v1` |

Put the tag in the training run's notes so a result can be traced to its data.

**Go back to an older version**

```bash
git checkout data-v1 -- data/chips.dvc data/annotations.dvc   # old pointers only
dvc pull                                                       # fetch that data
```

Use `dvc pull`, not `dvc checkout`. `checkout` only works for data already in
your local cache. To return to the latest: `git checkout main -- data/*.dvc && dvc pull`.

**Record where raw imagery came from.** Add a row to `data/PROVENANCE.md` for every
raw pull: source, year, bounding box, tile or STAC item ID, date pulled. This is
what lets us skip storing raw tiles (they can be re-fetched for free; see below).

## What not to put in the bucket

- **Anything that is not public domain or CC0.** NOAA Digital Coast imagery (CC0,
  our chosen source) and NAIP (public domain) are fine to store. Google, Bing and Mapbox imagery is not: their terms bar storing
  tiles and training on them (see the imagery licensing matrix). If the team
  later adopts Esri or another licensed source, get the license confirmed in
  writing before its imagery goes into the shared bucket.
- Secrets, credentials, personal data.
- Regenerable intermediate files (augmented chips, cached tiles).

## Cost and egress

Prices checked October 2026 from third-party comparison pages that cite each
provider; confirm on the provider's pricing page before committing a budget.

| | Storage / GB-month | Egress to internet |
|---|---|---|
| Cloudflare R2 | $0.015 (first 10 GB free) | $0, always |
| AWS S3 Standard | $0.023 | First 100 GB/month free, then $0.09/GB |
| Backblaze B2 | $0.00695 | Free up to 3x stored data, then $0.01/GB |

**Expected size (my estimates, not measured):**

| Item | Assumption | Size |
|---|---|---|
| ~100 annotated chips | 1024x1024, 4-band, 8-bit is about 4 MB uncompressed | under 0.5 GB |
| Masks | single-band, small | under 0.1 GB |
| Checkpoints | roughly 15 MB (SegFormer-B0) to 330 MB (B5) each; about 20 kept | 2 to 4 GB |
| Raw NOAA tiles | do not version, re-fetch | 0 |

That is **under about 5 GB, which fits inside R2's 10 GB free tier ($0/month)**. On
S3 the same 5 GB costs about $0.12/month in storage.

**Where egress starts to matter:** every pull is egress. Ten people each pulling 5 GB
once a week is about 200 GB/month. On S3 that is (200 - 100) x $0.09 = **about $9/month**;
on R2 it is $0. CI that pulls the full dataset on every run would multiply this,
so make CI pull only what a job needs (`dvc pull data/chips.dvc`).

**Tied to the imagery source (NOAA Digital Coast):**

- **License:** CC0 (public domain dedication), so storing derived chips and
  annotations in our bucket is allowed. Attribution is not legally required, but
  we keep a credit line in `data/PROVENANCE.md` anyway. Confirm the license on
  each dataset's Digital Coast page when you pull it; it is stated per dataset.
- **Where it comes from:** the sample tile we looked at is served from public Azure
  blob storage (`coastalimagery.blob.core.windows.net/digitalcoast/...`), with an
  `index.html` listing per dataset. No account or key is needed. I did not verify
  whether Azure bills the downloader for egress; for public anonymous blobs it is
  normally the storage owner (NOAA), but check before pulling at scale.
- **Tiles are heavier than NAIP.** NOAA's coastal flights are sharper (for example
  0.25 m, 4 bands plus alpha for the Port Jefferson 2026 set) than NAIP's 1 m, so a
  tile covers less ground per megabyte and costs more per square kilometre to store.
  I have not measured tile sizes, so the size table above is still an estimate
  and gets worse if we version raw tiles. That is why raw tiles stay out of the
  bucket: version chips only and re-fetch tiles from the source.
- **Coverage is coastal only.** Digital Coast covers specific coastal projects and
  years, not the whole country. Record the dataset name and year in
  `data/PROVENANCE.md` so a pull can be repeated.
- **For the MVP the source costs $0**, since downloads are free and we only keep
  chips. **Egress we pay** is only the DVC bucket traffic in the table above.
- NAIP stays a fallback for areas NOAA does not cover. Its AWS buckets
  (`naip-analytic`, `naip-source`, `naip-visualization`, us-west-2) are
  Requester Pays, so prefer the free USGS ImageServer if we ever use it.

## One-time admin setup (not done yet)

One person does this once. Takes about 10 minutes.

1. Create a Cloudflare account, enable R2, and create a **private** bucket, for
   example `cloudtcp-geospatial`.
2. In R2, create an API token with **Object Read & Write**, scoped to that bucket
   only. Better: one token per teammate so one can be revoked on its own.
3. Put the real values into the committed config (these are not secrets):

   ```bash
   dvc remote modify storage url s3://cloudtcp-geospatial/dvc
   dvc remote modify storage endpointurl https://<ACCOUNT_ID>.r2.cloudflarestorage.com
   git add .dvc/config && git commit -m "storage: point DVC at the R2 bucket" && git push
   ```
4. Hand each teammate their key pair through a password manager.
5. Seed it and check it:

   ```bash
   dvc add data/chips data/annotations
   git add data/*.dvc data/.gitignore && git commit -m "data: first chip set"
   dvc push && git push
   ```
   A second person then runs `git pull && dvc pull` to confirm it works for them.

To use AWS S3 instead, remove the endpoint and point `url` at the S3 bucket:

```bash
dvc remote modify storage --unset endpointurl
dvc remote modify storage url s3://<your-s3-bucket>/dvc
```

## Verify your install

```bash
bash scripts/storage_smoke_test.sh
```

Builds a throwaway repo and remote in a temp folder and proves push, pull, and
restore-an-old-version all work. It needs no cloud account and never touches this
repo.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `dvc pull` says a file is missing from the remote | Someone ran `git push` without `dvc push`. Ask them to run `dvc push`. |
| `dvc checkout` fails for an old tag | The old data is not cached locally. Use `dvc pull`. |
| `Unable to locate credentials` or 403 | Credentials not set locally; redo "One-time setup". |
| `REPLACE-WITH-BUCKET` in an error | Admin setup (step 3) has not been committed yet. |
