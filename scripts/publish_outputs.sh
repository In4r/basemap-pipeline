#!/usr/bin/env bash
# Validate emitted geometry documents, then version them in storage.
#
#   generate-basemap <bbox...> --out-dir data/outputs/geometry
#   bash scripts/publish_outputs.sh
#
# Validation runs first so a malformed document never reaches the bucket.
# Afterwards, commit the pointer file and push (storage first, then git), see docs/storage.md.
set -euo pipefail

DIR="data/outputs/geometry"
shopt -s nullglob
files=("$DIR"/*.json)
if [ ${#files[@]} -eq 0 ]; then
  echo "No documents in $DIR. Run generate-basemap --out-dir $DIR first." >&2
  exit 1
fi

validate-geometry "${files[@]}"
dvc add data/outputs
dvc push
echo
echo "Uploaded. Now share the pointer file:"
echo "  git add data/outputs.dvc data/.gitignore"
echo "  git commit -m 'outputs: geometry documents <what changed>'"
echo "  git tag outputs-vN    # optional, for a version worth returning to"
echo "  git push --follow-tags"
