#!/bin/sh
# macOS arm64 bootstrap: needs only vendor OS sh/curl/tar/shasum, not system Python/uv.
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
DATA=${SEAGENT_FREECAD_DATA:-"$HOME/Library/Application Support/SEAgentFreeCAD"}
case "$(uname -s)-$(uname -m)" in Darwin-arm64) ;; *) echo '目前仅验证macOS arm64；拒绝安装其他平台运行时。' >&2; exit 2;; esac
mkdir -p "$DATA/downloads" "$DATA/runtime"
fetch() {
  dest=$1; url=$2; expected=$3
  if [ -f "$dest" ] && [ "$(shasum -a 256 "$dest" | cut -d ' ' -f 1)" = "$expected" ]; then return; fi
  curl --connect-timeout 20 --max-time 300 --retry 2 --retry-delay 2 --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$url" -o "$dest.part"
  actual=$(shasum -a 256 "$dest.part" | cut -d ' ' -f 1)
  if [ "$actual" != "$expected" ]; then echo "下载校验失败：$dest" >&2; exit 3; fi
  mv "$dest.part" "$dest"
}
# Locked public distribution artifacts. Never execute download before hash verification.
fetch "$DATA/downloads/uv.tar.gz" 'https://github.com/astral-sh/uv/releases/download/0.11.14/uv-aarch64-apple-darwin.tar.gz' '4333af5c0730d94323a7819bbdf87ce92dd07fc857d67fff0059e0fca31b5c02'
fetch "$DATA/downloads/python.tar.gz" 'https://releases.astral.sh/github/python-build-standalone/releases/download/20260510/cpython-3.12.13%2B20260510-aarch64-apple-darwin-install_only_stripped.tar.gz' '55bc1a5edbc8ac4da0081f4f5731ed2d1ed10c57cb37a820b2a0dbc7cad742e9'
fetch "$DATA/downloads/upstream.tar.gz" 'https://codeload.github.com/neka-nat/freecad-mcp/tar.gz/8babe9927ce8e6e8fe7dd6ae2ffa2c93776e845a' 'f2d623d0d1dec086a46e156d2d169c0456b52a81db5593134b641e7baa08870f'
# tar's native safety rejects absolute/.. entries; also reject these paths before extraction.
for archive in uv python upstream; do
  if tar -tzf "$DATA/downloads/$archive.tar.gz" | /usr/bin/awk '/^\// || /(^|\/)\.\.(\/|$)/ {bad=1} END {exit !bad}'; then
    echo '非法归档路径，拒绝解压' >&2; exit 4
  fi
done
if [ "${1:-}" = '--download-only' ]; then echo '下载及完整性校验完成，未安装。' >&2; exit 0; fi
if [ ! -d "$DATA/runtime/uv" ]; then
  mkdir "$DATA/runtime/uv.partial"
  tar -xzf "$DATA/downloads/uv.tar.gz" -C "$DATA/runtime/uv.partial" --strip-components 1
  mv "$DATA/runtime/uv.partial" "$DATA/runtime/uv"
fi
if [ ! -d "$DATA/runtime/python" ]; then
  mkdir "$DATA/runtime/python.partial"
  tar -xzf "$DATA/downloads/python.tar.gz" -C "$DATA/runtime/python.partial" --strip-components 1
  mv "$DATA/runtime/python.partial" "$DATA/runtime/python"
fi
PYTHON="$DATA/runtime/python/bin/python3.12"
# Python3.12 data filter rejects escaping symlink targets as well as archive path traversal.
"$PYTHON" "$ROOT/scripts/install.py" "$DATA" "$ROOT"
export UV_HTTP_TIMEOUT=120
export UV_HTTP_RETRIES=2
export UV_CACHE_DIR="$DATA/downloads/uv-cache"
export UV_NO_MANAGED_PYTHON=1
export UV_PROJECT_ENVIRONMENT="$DATA/runtime/.venv"
if [ ! -x "$DATA/runtime/.venv/bin/python" ]; then
  "$DATA/runtime/uv/uv" venv --python "$PYTHON" "$DATA/runtime/.venv" >&2
fi
"$DATA/runtime/uv/uv" pip install --python "$DATA/runtime/.venv/bin/python" --require-hashes -r "$ROOT/build-requirements.lock" >&2
"$DATA/runtime/uv/uv" sync --frozen --no-dev --no-editable --inexact --no-build-isolation --python "$PYTHON" --directory "$DATA/runtime/upstream" >&2
printf '%s\n' 'SEAgent FreeCAD runtime ready (0.1.0)' > "$DATA/runtime/READY"
"$DATA/runtime/.venv/bin/python" "$ROOT/scripts/manage.py" inventory
echo '运行时准备完成。下一步configure；未启动FreeCAD，未修改全局Addon或手动MCP。' >&2
