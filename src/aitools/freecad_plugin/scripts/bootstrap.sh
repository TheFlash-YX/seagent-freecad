#!/bin/sh
# macOS arm64 bootstrap: needs only vendor OS sh/curl/tar/shasum, not system Python/uv.
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
DATA=${SEAGENT_FREECAD_DATA:-"$HOME/Library/Application Support/SEAgentFreeCAD"}
case "$(uname -s)-$(uname -m)" in Darwin-arm64) ;; *) echo '目前仅验证macOS arm64；拒绝安装其他平台运行时。' >&2; exit 2;; esac
# Resolve existing ancestors without depending on a system Python. Check before writes.
resolve_path() {
  candidate=$1; suffix=''
  case "$candidate" in /*) ;; *) candidate="$PWD/$candidate";; esac
  while [ ! -d "$candidate" ]; do
    suffix="/$(basename "$candidate")$suffix"; candidate=$(dirname "$candidate")
  done
  (CDPATH='' cd -- "$candidate" && printf '%s%s\n' "$(pwd -P)" "$suffix")
}
DATA=$(resolve_path "$DATA")
REPO=$(CDPATH='' cd -- "$ROOT/../../.." && pwd -P)
case "$DATA/" in "$REPO/"*) echo 'DATA与插件源码重叠' >&2; exit 4;; esac
case "$REPO/" in "$DATA/"*) echo 'DATA包含插件源码' >&2; exit 4;; esac
case "$DATA" in */../*|*/..|*/./*|*/.) echo 'DATA路径必须规范化' >&2; exit 4;; esac
for item in runtime downloads runtime/upstream runtime/upstream.partial runtime/.venv runtime/python runtime/uv runtime/python.partial runtime/uv.partial runtime-use.lock runtime/READY runtime/READY.previous upstream-files.json source-transaction.json; do
  if [ -L "$DATA/$item" ]; then echo "拒绝链接路径：$item" >&2; exit 4; fi
done
for marker in .git AGENTS.md pyproject.toml package.json; do
  if [ -e "$DATA/$marker" ]; then echo 'DATA指向项目源码' >&2; exit 4; fi
done
# A previous compatible private Python can preflight before any remote preparation.
if [ -x "$DATA/runtime/python/bin/python3.12" ]; then
  "$DATA/runtime/python/bin/python3.12" "$ROOT/scripts/install.py" "$DATA" "$ROOT" --action preflight
fi
mkdir -p "$DATA/downloads" "$DATA/runtime"
if ! mkdir "$DATA/.bootstrap-lock"; then echo '已有安装或中断锁，检查后显式移出.bootstrap-lock' >&2; exit 4; fi
trap 'rmdir "$DATA/.bootstrap-lock"' EXIT HUP INT TERM
fetch() {
  dest=$1; url=$2; expected=$3
  if [ -L "$dest" ] || [ -L "$dest.part" ]; then echo "拒绝链接下载目标：$dest" >&2; exit 4; fi
  if [ -f "$dest" ] && [ "$(shasum -a 256 "$dest" | cut -d ' ' -f 1)" = "$expected" ]; then return; fi
  curl --connect-timeout 20 --max-time 300 --retry 2 --retry-delay 2 --fail --location --silent --show-error --proto '=https' --tlsv1.2 "$url" -o "$dest.part"
  actual=$(shasum -a 256 "$dest.part" | cut -d ' ' -f 1)
  if [ "$actual" != "$expected" ]; then echo "下载校验失败：$dest" >&2; exit 3; fi
  mv "$dest.part" "$dest"
}
# Locked public distribution artifacts. Never execute download before hash verification.
fetch "$DATA/downloads/uv.tar.gz" 'https://github.com/astral-sh/uv/releases/download/0.11.14/uv-aarch64-apple-darwin.tar.gz' '4333af5c0730d94323a7819bbdf87ce92dd07fc857d67fff0059e0fca31b5c02'
fetch "$DATA/downloads/python.tar.gz" 'https://releases.astral.sh/github/python-build-standalone/releases/download/20260510/cpython-3.12.13%2B20260510-aarch64-apple-darwin-install_only_stripped.tar.gz' '55bc1a5edbc8ac4da0081f4f5731ed2d1ed10c57cb37a820b2a0dbc7cad742e9'
# tar's native safety rejects absolute/.. entries; also reject these paths before extraction.
for archive in uv python; do
  if tar -tzf "$DATA/downloads/$archive.tar.gz" | /usr/bin/awk '/^\// || /(^|\/)\.\.(\/|$)/ {bad=1} END {exit !bad}'; then
    echo '非法归档路径，拒绝解压' >&2; exit 4
  fi
done
if [ "${1:-}" = '--download-only' ]; then echo '仅uv/Python下载及完整性校验完成，未安装；不是完整离线包。' >&2; exit 0; fi
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
# Verify the complete bundled snapshot; no upstream archive or online fallback.
"$PYTHON" "$ROOT/scripts/install.py" "$DATA" "$ROOT"
"$PYTHON" "$ROOT/scripts/install.py" "$DATA" "$ROOT" --action environment-run
echo '运行时准备完成。下一步configure；未启动FreeCAD，未修改全局Addon或手动MCP。' >&2
