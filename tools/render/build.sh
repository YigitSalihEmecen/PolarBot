#!/bin/sh
# Regenerates every README visual from hardware/stl into ./out
set -e
cd "$(dirname "$0")"
mkdir -p out
for f in make_*.py; do python3 "$f"; done
