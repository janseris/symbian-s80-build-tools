#!/bin/sh
# prep6 (C) against r3_prep6 (ARM assembly) in the emulator, from a Maps 9300 checkout:
#   PATH: arm-epoc-pe-gcc;  pip install unicorn
#   ./build_prep6.sh [path/to/maps9300] [cases]      (default ../../../../../maps9300, 3000)
set -e
HERE=$(cd "$(dirname "$0")" && pwd)
M=${1:-$HERE/../../../../../maps9300}
OUT=${TMPDIR:-/tmp}/prep6emu
"$HERE/../../build_emu.sh" "$OUT" -I"$M/inc" -I"$M/dsp" "$HERE/drvprep6.cpp" "$M/src/r3dgeo.c" "$M/src/r3dspan.c" "$M/src/fastmem.c"
python3 "$HERE/../../asmcmp.py" "$OUT/emu.exe" "$OUT/emu.sym" "$HERE/prep6spec.py" ${2:-3000}
