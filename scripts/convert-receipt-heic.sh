#!/usr/bin/env bash
# Converts all pending HEIC receipts in reciepts/ to compressed JPEGs in /tmp/.
# Prints one output path per line. Skips files already in reciepts/processed/.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
RAW_DIR="$REPO_DIR/reciepts"
OUT_DIR="${1:-/tmp}"

found=0
while IFS= read -r -d '' heic; do
  base="$(basename -- "$heic")"
  stem="${base%.*}"
  out="$OUT_DIR/receipt-${stem}.jpg"
  sips -s format jpeg -s formatOptions 40 -Z 1200 "$heic" --out "$out" >/dev/null
  echo "$out"
  found=$((found + 1))
done < <(find "$RAW_DIR" -maxdepth 1 \( -iname "*.heic" -o -iname "*.jpg" -o -iname "*.png" \) -print0)

if [ "$found" -eq 0 ]; then
  echo "No pending receipts found in $RAW_DIR" >&2
fi
