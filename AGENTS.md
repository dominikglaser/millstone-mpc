# AGENTS.md — instructions for AI coding agents

This repo is **Millstone MPC**: the MPC-only build of the Millstone synth, a plugin for Akai MPC standalone hardware.
The released macOS Millstone lives in a separate repo (github.com/dominikglaser/millstone) and is **not** changed from here.

Akai's official **MPC Plugin SDK** specifications are vendored in [`docs/akai-sdk/`](docs/akai-sdk/README.md). They are
the authority for the folder format, the host's behaviour and the UI rules. Read the relevant file before changing
packaging, the engine's host-facing behaviour or the skin.

## How Millstone differs from an SDK plugin

The SDK expects a plugin written against its `framework/mpc_plugin.h` and built with its `tools/build.py`. Millstone is
not: its engine (`src/millstone.cpp`, C++14) is wrapped as a VST2 by the **Open MPC port kit**
(github.com/open-mpc/mpc-vst-plugins, checked out at `../mpc-vst-plugins` or `$MPC_VST`), which also renders the skin.
The resulting binary and skin are the same format the SDK produces (VST2 ABI `.so`, `TUI.json`, `Q-Links.json`), so
only the packaging step comes from the SDK spec. Do not port Millstone to the SDK framework, and do not use the SDK's
skills or `build.py` here: they assume a project layout this repo does not have.

| Piece | Where |
|---|---|
| Parameters (single source of truth; ids and order are permanent) | `vst/params.json` |
| Plugin identity, sources, defines | `vst/vst.json` (name `Millstone`, vendor `glaser`, uid `Mlst`) |
| Touchscreen skin: theme and top-level settings (Force Shadow layout syntax, rendered by the kit) | `vst/layout.conf` (top) |
| Every page of the skin: GENERATED, edit the generator, not the `[tab]` sections | `vst/skin/pages.py` |
| Skin artwork (Pillow) and stylesheet | `vst/skin/make_art.py`, `vst/skin/skin.css` |
| Local patch the port kit needs (dropdown closes on a tap outside) | `vst/kit-patches/` |
| Function-key grouping of the skin's pages (sub-tabs) | `FN_KEYS` in `vst/package_mpc.py` |
| Factory presets as .xpl files (tile page) and the PRESETS page's type table | `vst/make_xpl.py`, `vst/gen_preset_types.py` |
| SDK-format packaging | `vst/package_mpc.py` |
| SDK-rule check of the packaged folder | `tools/check_mpc_folder.py` |
| Engine, fx, vendored Mutable DSP | `src/millstone.cpp`, `src/fx/`, `src/third_party/eurorack/` |
| Presets | `vst/presets.json` and the `vst/pack_*.py` generators |

## Build, test, package

```sh
export MPC_VST=~/mpc-vst-plugins
python3 "$MPC_VST/tools/gen_vst.py" vst/vst.json --params-h   # vst/build/params.h
python3 "$MPC_VST/tools/gen_vst.py" vst/vst.json              # skin -> vst/build/skin/ (needs vst/build/shadow_art, see README)
vst/build_zig.sh aarch64 && vst/build_zig.sh armv7            # Gen2 (64-bit) and Gen1 (32-bit) .so
tools/run_tests.sh 300                                        # engine test, fx test, 300-patch fuzz
python3 vst/package_mpc.py --zip                              # dist/glaser - VST - Millstone/ (+ zip)
python3 tools/check_mpc_folder.py "dist/glaser - VST - Millstone" --params vst/build/params.h
```

Never report a build as done unless `run_tests.sh` passes and `check_mpc_folder.py` reports 0 errors. Akai's own
`tools/validate.py` and `host-sim` (from the SDK repo) are the stronger checks; run them when they are available.

## Skin rules learned on the device (Key 37 Gen 2, MPC OS 3.10.1)

- Knob radius at most 54: at 59 the 128-frame filmstrip reaches MPC's 16384 px limit and the knob is drawn garbled.
- Knob and switch names are printed into the art (`text` lines from `pages.py`): MPC's live name would be the long
  parameter name ("OSC1 HARMONICS"). The live value sits under it (`vy`, `vs`).
- A dropdown's value text takes `theme_accent` (`tcolor` only works on readouts and steppers).
- The renderer clips CSS shadows at a control's image box: bake shadows into the image with margin (`make_art.py`).
- MPC's PRESET menu is one flat list for a VST2; the PRESETS page (params `p_type`/`p_preset`, engine
  `load_typed_preset`) gives categories. The tile page loads `.xpl` presets only while the program list exists.
- Check a page on the device with `tools/mpc_screenshot.sh <ip> shot.png --plugin`.

## Installing on an MPC (the official route)

MPC OS **3.10.1 or later**. On the MPC: Preferences → Enhancements (Beta) → turn on **Enable Enhancements** and
**External Plugin Support**. Copy `dist/glaser - VST - Millstone/` into a folder named exactly `VST2 Plugins` at the root
of a USB stick, SD card or the internal drive, and restart the MPC. Millstone is listed under **External Plugins**.
Tell the user both requirements (firmware and switches) whenever you hand over a build. No root, no helper apps, no edits
to MPC system files: do not suggest them for this repo.

## Hard rules (from the SDK spec, applied to Millstone)

- **Identity is permanent.** `uid` `Mlst`, the name/vendor strings, and parameter keys and order in `vst/params.json`
  must not change once projects exist; append new parameters at the end. The folder name, `plugin.json`
  `name`/`manufacturer` and the strings the binary reports must agree, or the MPC shows the default UI.
- **Binaries:** aarch64 (`file64`, Gen2: Live III, XL, One G2, Key 37 Gen 2) and armv7 hard-float (`file32`, Gen1).
  glibc symbol versions ≤ 2.39 (we are at 2.34 / 2.27), only libc/libm/libpthread/libdl, static C++ runtime, export
  **only** `VSTPluginMain` (`vst/exports.map`). Note: Akai's docs list "Key 37" as 32-bit; that is the Gen1 Key 37.
- **Host:** 44.1 kHz fixed; frames per call vary 32–512 (the announced block size is a maximum); no allocation, locks,
  I/O or logging on the audio thread; parameter changes can arrive from the UI thread while processing runs.
  **Parameter 0 (VOICES) is nudged to 0/1 and back on every prepare**; this is harmless because the voice count is only
  read at note allocation. Keep it that way, or put a harmless parameter first (never reorder existing ones, though).
- **UI** (`docs/akai-sdk/ui-guide.md`, `ui-reference.md` §10): ≤ 16 controls per page, arranged in blocks of four that
  match the Q-Link columns; page labels (the `qlinks "..."` titles) ≤ 8 characters; ≤ 32 tabs and ≤ 8 sub-tabs per
  function key; keep controls left of x ≈ 1010 (the Q-Link sidebar); same widget for the same job on every page.
  `Program Mode Q-Links` (`qlinks_track` in `vst/layout.conf`) hold the 16 most important parameters.
- **version.xml** `<uiversion>` is exactly `0.1.0.0` (never `1`: the MPC would refuse the plugin).
- **Nothing proprietary:** no files from MPC firmware or Steinberg's VST SDK. Everything here is MIT; keep it that way.
- Commit, push and merge only when the user asks.

## Device status

Not yet tested on hardware. Track results in [`TESTING.md`](TESTING.md). The open question is CPU: 8 voices ×
(3 Plaits + Elements + Tides) + 8 clocks + fx on the Key 37 Gen 2 may need a lower voice cap.
