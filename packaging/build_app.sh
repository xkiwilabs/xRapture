#!/usr/bin/env bash
# Build the standalone macOS app bundle: dist/xRapture.app
#
#   bash packaging/build_app.sh
#
# Set PYBIN to use a specific interpreter (defaults to the repo's .venv).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
cd "$ROOT"

PYBIN="${PYBIN:-$ROOT/.venv/bin/python}"
echo "==> Using interpreter: $PYBIN"

echo "==> Installing build dependencies (editable + dev extras)"
"$PYBIN" -m pip install -e ".[dev]" >/dev/null

echo "==> Generating app icon"
"$PYBIN" packaging/make_appicon.py
if command -v iconutil >/dev/null 2>&1; then
    iconutil -c icns "$HERE/xRapture.iconset" -o "$HERE/xRapture.icns"
    echo "    wrote $HERE/xRapture.icns"
else
    echo "    (iconutil not found — building without a custom icon)"
fi

echo "==> Building with PyInstaller (this can take a few minutes)"
"$PYBIN" -m PyInstaller --noconfirm --clean \
    --distpath "$ROOT/dist" --workpath "$ROOT/build" \
    "$HERE/xrapture.spec"

echo ""
echo "==> Done. App bundle: dist/xRapture.app"
echo "    Try it:   open dist/xRapture.app"
echo "    Install:  cp -R dist/xRapture.app /Applications/"
