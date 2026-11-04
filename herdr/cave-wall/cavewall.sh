#!/bin/sh
# entry point: cavewall [board|seed|hook]
PYTHONPATH="$(dirname "$(readlink -f "$0")")" exec python3 -m cavewall "$@"
