#!/usr/bin/env bash
# A screenshot of the MPC's screen as it is right now (read-only), without Docker:
#   tools/mpc_screenshot.sh <mpc ip> out.png [--plugin]     (--plugin crops to the 1280x628 plugin area)
# Builds the port kit's tools/drmgrab.c for aarch64 (Gen2) with Zig, copies it to /tmp on the MPC over SSH
# (developer mode), runs it once, deletes it, and converts the raw framebuffer with Pillow.
set -euo pipefail
[ $# -ge 2 ] || { sed -n 2,5p "$0"; exit 1; }
ROOT=$(cd "$(dirname "$0")/.." && pwd); MV=${MPC_VST:-$ROOT/../mpc-vst-plugins}
IP=$1; OUT=$2; CROP=${3:-}
BIN=$ROOT/build/tools/drmgrab
if [ ! -x "$BIN" ] || [ "$MV/tools/drmgrab.c" -nt "$BIN" ]; then
  Z=$(python3 -c "import ziglang,os;print(os.path.dirname(ziglang.__file__))")
  mkdir -p "$(dirname "$BIN")"
  python3 -m ziglang cc -target aarch64-linux-musl -static -O2 -I"$Z/lib/libc/include/any-linux-any/drm" -o "$BIN" "$MV/tools/drmgrab.c"
fi
SSH=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR -o ConnectTimeout=8)
RAW=$(mktemp)
trap 'rm -f "$RAW"' EXIT
ssh "${SSH[@]}" "root@$IP" 'cat > /tmp/drmgrab && chmod +x /tmp/drmgrab && { /tmp/drmgrab /dev/dri/card0 || /tmp/drmgrab /dev/dri/card1; }; rc=$?; rm -f /tmp/drmgrab; exit $rc' < "$BIN" > "$RAW"
python3 - "$RAW" "$OUT" "$CROP" <<'PY'
import sys
from PIL import Image
raw = open(sys.argv[1], "rb").read(); hdr, px = raw.split(b"\n", 1)
w, h, p = map(int, hdr.split()[:3])
im = Image.frombuffer("RGBA", (w, h), px[:p * h], "raw", "BGRA", p, 1).convert("RGB")
im = im.rotate(270, expand=True) if h > w else im
if sys.argv[3] == "--plugin":
    im = im.crop((0, 110, 1280, 738))
im.save(sys.argv[2], optimize=True)
print("wrote", sys.argv[2], im.size)
PY
