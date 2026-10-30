#!/bin/sh
set -eu
ROOT=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
/bin/sh "$ROOT/src/aitools/freecad_plugin/scripts/bootstrap.sh"
exec "$HOME/Library/Application Support/SEAgent/FreeCAD/runtime/.venv/bin/python" "$ROOT/src/aitools/freecad_plugin/scripts/wizard.py"
