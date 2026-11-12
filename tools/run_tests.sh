#!/usr/bin/env bash
# All the JUCE-free checks for the MPC build: engine, fx and the fuzzer.
# Needs MPC_VST (a checkout of open-mpc/mpc-vst-plugins). Usage: tools/run_tests.sh [fuzz_patches]
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
MV=${MPC_VST:-$ROOT/../mpc-vst-plugins}
PATCHES=${1:-500}
OUT=$ROOT/build/tests
mkdir -p "$OUT"
cd "$ROOT"

python3 "$MV/tools/gen_vst.py" vst/vst.json --params-h >/dev/null
python3 vst/gen_preset_types.py >/dev/null || exit 1   # vst/build/preset_types.h for the PRESETS page
SRC=$(python3 -c "import json;print(' '.join(json.load(open('vst/vst.json'))['build']['sources']))")
INC="-Isrc -Isrc/third_party/eurorack -Ivst/build -I$MV/wrapper"
FLAGS="-std=gnu++14 -O2 -ffast-math -w -DTEST -include cstdio $INC"

echo "== engine test =="
g++ $FLAGS $SRC tests/engine_test.cpp -lm -o "$OUT/engine_test"
"$OUT/engine_test"

echo "== fx test =="
g++ -std=gnu++14 -O2 -w -DTEST -include cstdio -Isrc -Isrc/fx -Isrc/third_party/eurorack src/fx/*.cpp tools/fx_test.cpp -lm -o "$OUT/fx_test"
"$OUT/fx_test"

echo "== engine fuzz ($PATCHES patches) =="
g++ $FLAGS $SRC tools/engine_fuzz.cpp -lm -o "$OUT/engine_fuzz"
"$OUT/engine_fuzz" "$PATCHES"
