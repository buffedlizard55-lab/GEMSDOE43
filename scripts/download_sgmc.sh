#!/usr/bin/env bash
# Fetch the exact official USGS SGMC v1.1 source archives used by H46-B.
# Raw archives remain ignored under data/raw/ and must not be committed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$ROOT/data/raw/external/sgmc}"
mkdir -p "$DEST"

fetch_pinned() {
  local name="$1" url="$2" bytes="$3" hash="$4"
  local output="$DEST/$name"
  curl --fail --location --retry 4 --retry-all-errors --connect-timeout 30 --max-time 600 \
    --output "$output" "$url"
  [[ "$(wc -c < "$output" | tr -d ' ')" == "$bytes" ]] || {
    echo "Size mismatch for $name" >&2; exit 1;
  }
  echo "$hash  $output" | sha256sum --check
}

fetch_pinned 'CA.zip' \
  'https://mrdata.usgs.gov/geology/state/shp/CA.zip' \
  24977406 '78765ba4428df9f25a84f86e0b2529bd0508fc8a2cf65d2f41a830e82bccfd58'
fetch_pinned 'NV.zip' \
  'https://mrdata.usgs.gov/geology/state/shp/NV.zip' \
  69056094 '3b333ac025e59aae7f0d827db45ba32c425cf867eb341561a788af1de186b76b'
fetch_pinned 'USGS_SGMC_Tables_CSV.zip' \
  'https://www.sciencebase.gov/catalog/file/get/5888bf4fe4b05ccb964bab9d?name=USGS_SGMC_Tables_CSV.zip' \
  1573709 '8859dd1f00ec6ec3d397634dc86fa288e440b432aad8a98a5fb0c7f9b6bc0bde'

file "$DEST/CA.zip" "$DEST/NV.zip" "$DEST/USGS_SGMC_Tables_CSV.zip"
echo "Verified official SGMC v1.1 archives are stored under $DEST."
