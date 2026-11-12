# Akai MPC Plugin SDK documentation (vendored)

These are the specification documents of Akai's official **MPC Plugin SDK**, copied unchanged from
<https://github.com/inmusic-software/mpc-plugin-builder-sdk> at commit `febd2ca` (2026-11-07). They are MIT licensed
(© 2026 inMusic Brands, Inc., see [`LICENSE`](LICENSE)). The SDK's framework, tools, examples and UI kit are not copied:
Millstone is built with the Open MPC port kit, not with the SDK framework (see [`AGENTS.md`](../../AGENTS.md)).

When updating, re-copy `docs/*.md` from a newer SDK commit and change the commit above.

| File | What it settles for Millstone |
|---|---|
| [overview.md](overview.md) | Mental model: a VST2-ABI `.so` in a folder, UI as JSON data, parameters are the interface |
| [plugin-folder-format.md](plugin-folder-format.md) | **The install format**: `VST2 Plugins/<Manufacturer> - VST - <Name>/`, `plugin.json`, `version.xml`, binary rules (exports, glibc, libraries) |
| [host-contract.md](host-contract.md) | What the MPC host does: 44.1 kHz fixed, 32–512 frame blocks, in-place buffers, threads, load sequence, parameter 0 nudge, state chunks |
| [ui-guide.md](ui-guide.md) | Page and Q-Link design rules: blocks of four, labels ≤ 8 characters, widget choice |
| [ui-reference.md](ui-reference.md) | The full `TUI.json` / `Q-Links.json` format, limits (32 tabs, 8 sub-tabs per key), checklist in section 10 |
| [install-and-test.md](install-and-test.md) | Enabling External Plugin Support, copying to a drive, CPU expectations |
| [troubleshooting.md](troubleshooting.md) | Plugin not listed, no tabs, wrong knobs, crashes |
| [presets.md](presets.md) | Built-in programs and the MPC's `.xpl` files |
| [building.md](building.md) | Toolchains and flags (glibc 2.31 target, static C++ runtime) |
| [dsp-cookbook.md](dsp-cookbook.md) | Realtime DSP patterns (written for the SDK framework; the rules apply anyway) |
| [faq-and-legal.md](faq-and-legal.md) | Supported devices, VST2 trademark and licence notes |
