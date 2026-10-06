#!/usr/bin/env bash
# Restore pinned owner-mirrored competition inputs and the USGS-3DEP-derived LiDAR raster.
# Raw files remain under ignored data/raw/ and are never committed.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${1:-$ROOT/data/raw}"
mkdir -p "$DEST/competition" "$DEST/external"

FEATURE_REF='c0c06ac82178f26b94fce3397036ef8f12a2f3a0'
EXTERNAL_REF='07345ea0604953d7efb858d9cfbc21e20c7aca0b'
FEATURE_REPO='https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE'
EXTERNAL_REPO='https://raw.githubusercontent.com/buffedlizard55-lab/GEMSDOE24'

parts=(
  'gems-geodawn-numerical-features.tif.part-000 94371840 0a330f8951af6c921029e25c84a579319d2db554d62d30d894d6ddc97f98cff7'
  'gems-geodawn-numerical-features.tif.part-001 94371840 3c98037b2c997e3bbfcdfc2d9a982e8b820a77410dd7404b05cdb80594922c50'
  'gems-geodawn-numerical-features.tif.part-002 94371840 c375c4dbc40c59bbaece572b5e348700b75935f9a30c879c82b6417e0836f31c'
  'gems-geodawn-numerical-features.tif.part-003 94371840 b164159e6d0cb2595bc9f63a948af2646b124114a9c5921880c7516092137320'
  'gems-geodawn-numerical-features.tif.part-004 41425484 fa0a6f9c936fac1d6f20ca37f5929b2d60bf7a80f3d477dcab886f941aee2696'
)
feature="$DEST/competition/training_features.tif"
: > "$feature"
for entry in "${parts[@]}"; do
  read -r name bytes hash <<< "$entry"
  part="$DEST/competition/$name"
  curl --fail --location --retry 4 --retry-all-errors --connect-timeout 30 --max-time 300 \
    --output "$part" "$FEATURE_REPO/$FEATURE_REF/data/bridge/$name"
  actual_bytes="$(wc -c < "$part" | tr -d ' ')"
  actual_hash="$(sha256sum "$part" | cut -d' ' -f1)"
  [[ "$actual_bytes" == "$bytes" ]] || { echo "Size mismatch for $name: $actual_bytes != $bytes" >&2; exit 1; }
  [[ "$actual_hash" == "$hash" ]] || { echo "SHA-256 mismatch for $name" >&2; exit 1; }
  cat "$part" >> "$feature"
done
[[ "$(wc -c < "$feature" | tr -d ' ')" == '418912844' ]]
echo '4371c82e3b8339b807bdffcf4ef59a225520fe2988d521be208ae33743123bc5  '"$feature" | sha256sum --check

fetch_pinned() {
  local path="$1" output="$2" bytes="$3" hash="$4"
  curl --fail --location --retry 4 --retry-all-errors --connect-timeout 30 --max-time 180 \
    --output "$output" "$EXTERNAL_REPO/$EXTERNAL_REF/$path"
  [[ "$(wc -c < "$output" | tr -d ' ')" == "$bytes" ]] || { echo "Size mismatch: $path" >&2; exit 1; }
  echo "$hash  $output" | sha256sum --check
}
fetch_pinned 'data/bridge/labels.tif' "$DEST/competition/labels.tif" 425830 \
  '7ba308ccdc4418b31a178f4f1ef21aaa6e152e4028f2f6f64b01f7eb25ae4093'
fetch_pinned 'data/bridge/sample_submission.tif' "$DEST/competition/sample_submission.tif" 1599597 \
  '2176d08e485aa2cd2860ce8df539db4faf4d76163b38a4dd8c30a40454d35cbc'
fetch_pinned 'data/external/lidar_scarp_features_u8.tif' "$DEST/external/lidar_scarp_features_u8.tif" 36943606 \
  'd580bb8bdcdb941e32fefb8b38044bc5bf04e199bf2e83498c3576e6fc465568'

echo "Pinned raw inputs restored under $DEST (competition mirrors are integrity-pinned, not organizer-authenticated)."
