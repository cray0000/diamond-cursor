#!/bin/sh
# Render the README illustration at 2× its SVG size. Install librsvg2-bin on
# Ubuntu or librsvg on macOS. Fonts used in the reference image are DejaVu Sans
# and DejaVu Sans Mono (Ubuntu package fonts-dejavu-core).
set -eu

if ! command -v rsvg-convert >/dev/null 2>&1; then
    echo "Rendering requires rsvg-convert (Ubuntu: librsvg2-bin; macOS: brew install librsvg)." >&2
    exit 1
fi

asset_dir=$(CDPATH='' cd -- "$(dirname -- "$0")/../assets" && pwd)
temporary_png=$(mktemp "$asset_dir/.keyboard-map.XXXXXX")
trap 'rm -f "$temporary_png"' EXIT
rsvg-convert --zoom=2 --output="$temporary_png" "$asset_dir/keyboard-map.svg"
chmod 644 "$temporary_png"
mv -f "$temporary_png" "$asset_dir/keyboard-map.png"
