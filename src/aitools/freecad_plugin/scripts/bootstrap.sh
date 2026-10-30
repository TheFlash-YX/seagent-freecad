#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
DATA=${1:-"$HOME/Library/Application Support/SEAgent/FreeCAD"}
case "$DATA" in /*) ;; *) echo '请提供绝对机器目录' >&2; exit 2;; esac
case "$(uname -s)-$(uname -m)" in Darwin-arm64) ;; *) echo '此入口仅用于macOS arm64；Windows请用bootstrap.ps1' >&2; exit 2;; esac
mkdir -p "$DATA/downloads" "$DATA/runtime"
ARCHIVE="$DATA/downloads/python.tar.gz"
HASH=55bc1a5edbc8ac4da0081f4f5731ed2d1ed10c57cb37a820b2a0dbc7cad742e9
if [ ! -f "$ARCHIVE" ] || [ "$(shasum -a 256 "$ARCHIVE" | cut -d ' ' -f 1)" != "$HASH" ]; then
 curl --connect-timeout 20 --max-time 300 --retry 2 --fail --location --proto '=https' --tlsv1.2 'https://releases.astral.sh/github/python-build-standalone/releases/download/20260510/cpython-3.12.13%2B20260510-aarch64-apple-darwin-install_only_stripped.tar.gz' -o "$ARCHIVE.part"
 [ "$(shasum -a 256 "$ARCHIVE.part" | cut -d ' ' -f 1)" = "$HASH" ] || { echo 'Python下载校验失败' >&2; exit 3; }
 mv "$ARCHIVE.part" "$ARCHIVE"
fi
if [ ! -d "$DATA/runtime/python" ]; then
 [ ! -e "$DATA/runtime/python.partial" ] || { echo '保留中断python.partial，请检查' >&2; exit 4; }
 mkdir "$DATA/runtime/python.partial"
 # Archive is fixed/hash-checked. Reject member path traversal before system tar.
 tar -tzf "$ARCHIVE" | awk '/^\// || /(^|\/)\.\.(\/|$)/ {bad=1} END {exit bad}'
 tar -xzf "$ARCHIVE" -C "$DATA/runtime/python.partial" --strip-components 1
 mv "$DATA/runtime/python.partial" "$DATA/runtime/python"
fi
exec "$DATA/runtime/python/bin/python3.12" "$ROOT/scripts/bootstrap.py" --data "$DATA"
