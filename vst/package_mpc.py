#!/usr/bin/env python3
"""Assemble the Millstone plugin folder in Akai's MPC Plugin SDK format (MPC OS 3.10.1+).

    dist/glaser - VST - Millstone/
        plugin.json  version.xml
        VST/millstone-arm64.so   (and VST/millstone-arm32.so when an armv7 build exists)
        Plugin Skins/            (TUI.json, Q-Links.json, images, as rendered by gen_vst.py)

Copy that folder into "VST2 Plugins" at the root of a USB stick or SD card, then on the MPC turn on
Preferences > Enhancements (Beta) > Enable Enhancements and External Plugin Support.
Spec: https://github.com/inmusic-software/mpc-plugin-builder-sdk/blob/main/docs/plugin-folder-format.md

Run after a build:  python3 vst/package_mpc.py [--zip]
"""

import argparse
import json
import os
import shutil
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ILLEGAL = '"#@,;:<>*^|?\\/'  # characters the MPC strips when it builds the folder name

# Function keys, in signal-flow order. Each key holds sub-tabs (pages, by qlinks title in layout.conf):
# pressing the same key again cycles them (Akai: at most 8 sub-tabs per key, 32 tabs, labels <= 8 chars).
# The community kit gives every page its own key; this regroups the rendered skin.
FN_KEYS = [
    ["OSC 1", "OSC 2", "OSC 3", "ELEMENTS"],    # sound sources
    ["FLT/VCA"],
    ["ENV"],
    ["LFO1/VCE", "LFO 2", "TIDES"],             # modulators
    ["MOD 1-6", "MOD 7-12"],                    # mod matrix
    ["CLK 1-2", "CLK 3-4", "CLK 5-6", "CLK 7-8"],   # Euclidean clocks (patch-bay sources), two per page
    ["PHASER", "CHORUS", "DELAY", "REVERB"],    # FX chain order; REVERB holds the master OUTPUT
    ["PRESETS"],                                # the factory sounds by TYPE (MPC's own PRESET menu is one flat list)
]


def regroup_tabs(skins):
    """Put the rendered tabs on FN_KEYS as sub-tabs, in TUI.json and Q-Links.json alike."""
    where = {name: (k, s) for k, names in enumerate(FN_KEYS) for s, name in enumerate(names)}

    def load(path):
        def no_dupes(pairs):  # the overlay widgets' duplicate "version" keys would not survive json
            keys = [k for k, _ in pairs]
            if len(keys) != len(set(keys)):
                raise SystemExit("%s has duplicate keys; cannot regroup it with json" % path)
            return dict(pairs)
        return json.load(open(path), object_pairs_hook=no_dupes)

    tui_p, q_p = os.path.join(skins, "TUI.json"), os.path.join(skins, "Q-Links.json")
    tui, q = load(tui_p), load(q_p)
    tabs = tui["pageData"]["tabs"]
    qmap = q["Screen Mode Q-Links"]["map"]
    by_old = {(e["Tab"], e["SubTab"]): e for e in qmap}
    names = [t["tabName"] for t in tabs]
    missing = sorted(set(names) - set(where)) + sorted(set(where) - set(names))
    if missing or len(names) != len(set(names)):
        raise SystemExit("FN_KEYS and the layout's pages disagree: %s" % missing)
    new_q = []
    for t in tabs:
        e = by_old[(t["fnKeyIndex"] + 1, t["fnKeySubIndex"] + 1)]
        t["fnKeyIndex"], t["fnKeySubIndex"] = where[t["tabName"]]
        e["Tab"], e["SubTab"] = t["fnKeyIndex"] + 1, t["fnKeySubIndex"] + 1
        new_q.append(e)
    tabs.sort(key=lambda t: (t["fnKeyIndex"], t["fnKeySubIndex"]))
    new_q.sort(key=lambda e: (e["Tab"], e["SubTab"]))
    q["Screen Mode Q-Links"]["map"] = new_q
    with open(tui_p, "w") as f:
        json.dump(tui, f, indent=1)
    with open(q_p, "w") as f:
        json.dump(q, f, indent=2)
    # Hardware variant files (e.g. "Q-Links - 8by1.json" for the Force) carry the same tab numbers
    for fn in os.listdir(skins):
        if fn.startswith("Q-Links - ") and fn.endswith(".json"):
            p = os.path.join(skins, fn)
            v = load(p)
            for e in v["Screen Mode Q-Links"]["map"]:
                t = tabs_by_old_index(names, e)
                e["Tab"], e["SubTab"] = where[t][0] + 1, where[t][1] + 1
            v["Screen Mode Q-Links"]["map"].sort(key=lambda e: (e["Tab"], e["SubTab"]))
            with open(p, "w") as f:
                json.dump(v, f, indent=2)


def tabs_by_old_index(names, e):
    """The page name of a Q-Links entry as the kit numbered it: one key per page, sub-tab 1."""
    if e["SubTab"] != 1:
        raise SystemExit("unexpected sub-tab %s in a kit Q-Links file" % e["SubTab"])
    return names[e["Tab"] - 1]


def fourcc(s):
    assert len(s) == 4, s
    return sum(ord(c) << (8 * (3 - i)) for i, c in enumerate(s))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zip", action="store_true", help="also write dist/<folder>.zip with INSTALL.txt")
    args = ap.parse_args()

    cfg = json.load(open(os.path.join(HERE, "vst.json")))
    name, mfr = cfg["name"], cfg["vendor"]
    v = cfg["version"]  # 100 -> 1.0.0
    version = "%d.%d.%d" % (v // 100, v // 10 % 10, v % 10)
    folder = "".join(c for c in "%s - VST - %s" % (mfr, name) if c not in ILLEGAL)
    slug = os.path.splitext(cfg["so"])[0]

    build = os.path.join(HERE, "build")
    skins = os.path.join(build, "skin", folder, "Plugin Skins")
    if not os.path.isfile(os.path.join(skins, "TUI.json")):
        raise SystemExit("no rendered skin at %s: run gen_vst.py first" % skins)

    out = os.path.join(ROOT, "dist", folder)
    shutil.rmtree(out, ignore_errors=True)
    os.makedirs(os.path.join(out, "VST"))

    pj = {
        "name": name,
        "manufacturer": mfr,
        "version": version,
        "format": "vst2",
        "kind": "instrument",
        "uid": cfg["uid"],
        "category": "Synth",
        "numInputs": 0,
        "numOutputs": 2,
        "description": "Polyphonic synth: three Plaits oscillators, Elements, Tides, ladder filter, "
                       "12-cord mod matrix, 8 Euclidean clocks, phaser/chorus/tape delay/reverb.",
        "author": "Dominik Glaser",
        "license": "MIT",
    }
    for arch, key, tag in (("aarch64", "file64", "arm64"), ("armv7", "file32", "arm32")):
        so = os.path.join(build, arch, cfg["so"])
        if os.path.isfile(so):
            rel = "VST/%s-%s.so" % (slug, tag)
            shutil.copy2(so, os.path.join(out, rel))
            pj[key] = rel
    if "file64" not in pj and "file32" not in pj:
        raise SystemExit("no built .so in vst/build/<arch>/: build first")

    with open(os.path.join(out, "plugin.json"), "w") as f:
        json.dump(pj, f, indent=2)
        f.write("\n")

    # uiversion 0.1.0.0 exactly when skins ship (never "1": the MPC would refuse the plugin)
    with open(os.path.join(out, "version.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n<plugincontent version="1.0">\n'
                "    <version>%s.0</version>\n    <uiversion>0.1.0.0</uiversion>\n</plugincontent>\n" % version)

    shutil.copytree(skins, os.path.join(out, "Plugin Skins"),
                    ignore=shutil.ignore_patterns(".DS_Store", "._*"))
    regroup_tabs(os.path.join(out, "Plugin Skins"))

    # The Sounds > INSTRUMENTS tile. Tapping it opens the plugin's preset page, which lists Presets/ by category; the
    # PRESET menu in the plugin header only lists a plugin's own VST programs (device notes, MPC OS 3.9.1/3.10.1).
    tile = os.path.join(HERE, "tile.png")
    if os.path.isfile(tile):
        os.makedirs(os.path.join(out, "Plugin Skins", "browser_images"), exist_ok=True)
        shutil.copy2(tile, os.path.join(out, "Plugin Skins", "browser_images", "soundsmode.png"))

    # Factory presets as the stock instruments ship them: Presets/NNNN-Category-Name.xpl (vst/make_xpl.py)
    xpl = os.path.join(build, "presets_xpl")
    if os.path.isdir(xpl) and any(f.endswith(".xpl") for f in os.listdir(xpl)):
        shutil.copytree(xpl, os.path.join(out, "Presets"), ignore=shutil.ignore_patterns(".DS_Store", "._*"))
    else:
        print("note: no vst/build/presets_xpl/ (run tools/preset_states + vst/make_xpl.py): packaged without Presets/")

    print("packaged %s (%s)" % (out, ", ".join(k for k in ("file64", "file32") if k in pj)))

    if args.zip:
        zpath = os.path.join(ROOT, "dist", "Millstone-%s-mpc.zip" % version)
        install = ("Millstone %s for MPC OS 3.10.1 or later\n\n"
                   "1. Copy the folder \"%s\" into a folder named exactly \"VST2 Plugins\" at the root of a\n"
                   "   USB stick or SD card (create \"VST2 Plugins\" if needed).\n"
                   "2. On the MPC: Preferences > Enhancements (Beta): turn on Enable Enhancements and\n"
                   "   External Plugin Support, then restart.\n"
                   "3. Millstone is listed in the plugin browser under External Plugins.\n" % (version, folder))
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("INSTALL.txt", install)
            for dp, _, files in os.walk(out):
                for fn in sorted(files):
                    p = os.path.join(dp, fn)
                    z.write(p, os.path.relpath(p, os.path.dirname(out)))
        print("zipped %s" % zpath)


if __name__ == "__main__":
    main()
