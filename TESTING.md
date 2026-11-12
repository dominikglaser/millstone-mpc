# Testing

## Offline (x86)
- `tools/run_tests.sh [patches]`: all the JUCE-free checks in one go — the engine test, the fx test
  (each effect measured directly) and the engine fuzzer. Needs `MPC_VST` set to a checkout of the port kit.
- `tests/run.sh fast build/demo.wav`: just the engine tests (every model x every VCA mode makes sound and goes
  quiet, 3 oscillators + HP + drive + noise, polyphony and stealing, MONO note stack, LEGATO glide, sustain pedal,
  state round-trip, worst-case CPU timing) and a demo WAV. `tests/run.sh asan` runs the same under ASan/UBSan.
- `$MPC_VST/tools/test_port.sh vst/vst.json`: the port kit's wrapper-level host test. One known FAIL: the
  step_of "steps one option" check taps a button twice within a block, which the wrapper's tap debounce drops.

## Package (Akai SDK format)
- `python3 vst/package_mpc.py --zip` then `python3 tools/check_mpc_folder.py "dist/glaser - VST - Millstone" --params
  vst/build/params.h`: folder name, `plugin.json`, both binaries (architecture, libraries, glibc, only `VSTPluginMain`
  exported), `version.xml`, tabs and sub-tabs, parameter handles, images, Q-Links. It mirrors the SDK's
  `tools/validate.py`. Must report 0 errors.
- Stronger, from a checkout of Akai's SDK: `python3 tools/validate.py <folder>` and its host simulator
  (`host_sim <native build> test`), which loads the plugin the way the MPC does. Needs a native (macOS) build of the
  wrapper; not set up yet.

## Device (MPC OS 3.10.1+, External Plugin Support on, folder in `VST2 Plugins`)
| # | Check | Result |
|---|---|---|
| 1 | Plugin appears under External Plugins and loads on a track | OK (2026-11-12, Key 37 G2, 3.10.1.12) |
| 2 | Plays from pads / keys, polyphonic | OK (2026-11-12) |
| 3 | Skin pages draw, popups open and close (also on a tap outside), prev/next step | OK (2026-11-12) |
| 4 | Eight function keys; pressing a key again cycles its pages (OSC 1→2→3→ELEMENTS, CLK 1-2→…→7-8) | OK (2026-11-12) |
| 5 | Q-Links move the right knobs per page and per sub-tab | not yet run |
| 6 | Program Mode Q-Links: filter / ADSR / osc timbre-morph / LFO-mix-volume columns | not yet run |
| 7 | Save / reload project restores every parameter | not yet run |
| 8 | CPU: 8 voices x 3 Plaits, then Elements and Tides, clocks and fx (MPC CPU meter) | not yet run |
