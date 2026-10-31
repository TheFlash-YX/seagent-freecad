#!/bin/sh
# No stdout logging: this stream belongs to the unmodified upstream MCP.
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
DATA=${SEAGENT_FREECAD_DATA:-"$HOME/Library/Application Support/SEAgentFreeCAD"}
PYTHON="$DATA/runtime/.venv/bin/python"
if [ ! -x "$PYTHON" ] || [ ! -f "$DATA/config.json" ] || [ ! -f "$DATA/runtime/READY" ]; then
  echo 'SEAgent FreeCAD 尚未设置。按插件 README 运行 scripts/bootstrap.sh，再 configure；不会自动启动 FreeCAD。' >&2
  exit 78
fi
exec "$PYTHON" "$ROOT/scripts/manage.py" exec-mcp -- "$@"
