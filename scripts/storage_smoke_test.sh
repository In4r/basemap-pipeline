#!/usr/bin/env bash
# End-to-end check that DVC versioning works on this machine, with no cloud
# account needed. It builds a throwaway git repo + a throwaway local DVC
# remote in a temp folder, then proves four things:
#   1. data can be pushed to the remote
#   2. a second version of the same data can be pushed
#   3. after wiping the local copy and cache, the latest version can be pulled back
#   4. an OLDER version can be restored from a git tag
#
# Usage:   bash scripts/storage_smoke_test.sh
# Needs:   git and dvc on PATH   (pip install "dvc[s3]")
# It never touches your real repo or your real remote.

set -euo pipefail

command -v git >/dev/null || { echo "git not found"; exit 1; }
command -v dvc >/dev/null || { echo "dvc not found (pip install 'dvc[s3]')"; exit 1; }

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
REPO="$WORK/repo"
REMOTE="$WORK/remote"
mkdir -p "$REPO" "$REMOTE"
cd "$REPO"

git init -q
git config user.name "smoke-test"
git config user.email "smoke-test@example.com"
dvc init -q
dvc remote add -d smoke "$REMOTE" -q
git add -A && git commit -q -m "init dvc"

# ---- version 1: two fake chips + one fake label ---------------------------
mkdir -p data/chips
printf 'chip-a-v1' > data/chips/chip_a.tif
printf 'chip-b-v1' > data/chips/chip_b.tif
dvc add data/chips -q
git add data/chips.dvc data/.gitignore
git commit -q -m "chips v1"
git tag data-v1
dvc push -q
echo "ok 1/4  pushed data-v1"

# ---- version 2: change one chip, add another ------------------------------
printf 'chip-a-v2-relabeled' > data/chips/chip_a.tif
printf 'chip-c-v2' > data/chips/chip_c.tif
dvc add data/chips -q
git add data/chips.dvc
git commit -q -m "chips v2"
git tag data-v2
dvc push -q
echo "ok 2/4  pushed data-v2"

# ---- wipe local data and cache, then pull the latest ----------------------
rm -rf data/chips .dvc/cache
dvc pull -q
test "$(cat data/chips/chip_a.tif)" = "chip-a-v2-relabeled"
test -f data/chips/chip_c.tif
echo "ok 3/4  pulled latest (data-v2) from remote after wiping local copy"

# ---- restore the older version from its git tag ---------------------------
git checkout -q data-v1 -- data/chips.dvc
dvc pull -q   # pull, not checkout: the old version is not in the local cache yet
test "$(cat data/chips/chip_a.tif)" = "chip-a-v1"
test ! -f data/chips/chip_c.tif
echo "ok 4/4  restored data-v1 from git tag"

echo
echo "PASS: push, pull and version restore all work."
