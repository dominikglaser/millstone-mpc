#!/usr/bin/env python3
"""vst/build/preset_types.h: each factory preset's TYPE and list place, for the PRESETS page.

MPC's PRESET menu lists a VST2's presets as one flat list (only Akai's own plugin format gets category folders), so the
skin has its own browser: TYPE picks a category, PRESET steps through that category's presets in presets.json order.
The type names are p_type's options in params.json; every preset's "category" must be one of them (Riser/FX is
spelled "Riser & FX" there). Also checks that p_preset's max covers the largest category.

A double tap on PRESET opens a list of the type's names (a popup per list in the skin). A list holds at most LIST_MAX
names: a bigger type is split into two alphabetical halves (such as A-K / L-Z), each its own list. Every type has two
list params, p_pick_<type>_1 and _2 (fixed keys, so params.lock stays valid when a type grows or shrinks); p_list
names the list the current preset is in (the skin shows that list's popup); p_index is the preset's number in
presets.json, which every factory preset sets last, so MPC's own PRESET menu moves TYPE and PRESET along. The engine
keeps them all in sync.

    python3 vst/gen_preset_types.py            # writes vst/build/preset_types.h; fails if params.json's lists are stale
    python3 vst/gen_preset_types.py --params   # first rewrites the list params in params.json from presets.json

Run before compiling the engine (vst/build_zig.sh and tools/run_tests.sh do); make_presets.py runs --params.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ALIAS = {"Riser/FX": "Riser & FX"}
LIST_MAX = 60   # 5 columns x 12 rows of the skin's popup (vst/skin/pages.py); a bigger type is split in two
INDEX_MAX = 1023   # p_index's range: room for more presets without changing the param


def slug(t):
    return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_")


def boundary(a, b):
    """The shortest prefixes that tell a from b (at least one letter), for the labels around a split ("K" | "L")."""
    n = 1
    while n < min(len(a), len(b)) and a[:n].lower() == b[:n].lower():
        n += 1
    return a[:n].upper().strip(), b[:n].upper().strip()


def compute(params, presets):
    """-> (types, per-preset type index, per-type counts, lists). A list: dict(key, type, half, label, title, names, slots, presets)."""
    types = params["p_type"]["options"]
    idx, count = [], [0] * len(types)
    members = [[] for _ in types]   # (name, slot within its type, index in presets.json)
    for i, p in enumerate(presets):
        name = ALIAS.get(p["category"], p["category"])
        if name not in types:
            raise SystemExit("gen_preset_types: preset %r has category %r, not one of p_type's options %s"
                             % (p["name"], p["category"], types))
        t = types.index(name)
        idx.append(t)
        count[t] += 1
        members[t].append((p["name"], count[t], i))
    if max(count) > params["p_preset"]["max"]:
        raise SystemExit("gen_preset_types: the largest type has %d presets but p_preset's max is %g: raise it in params.json"
                         % (max(count), params["p_preset"]["max"]))
    if len(presets) - 1 > INDEX_MAX:
        raise SystemExit("gen_preset_types: %d presets, but p_index only reaches %d" % (len(presets), INDEX_MAX))
    lists = []
    for t, tname in enumerate(types):
        ms = sorted(members[t], key=lambda m: (m[0].lower(), m[1]))
        if len(ms) > LIST_MAX:
            # split where the first letter changes, as near the middle as that allows ("A-K" / "L-Z"); only if no letter
            # change keeps both halves within LIST_MAX does the split fall inside a letter (labels then use more letters)
            ok = [c for c in range(len(ms) - LIST_MAX, LIST_MAX + 1) if 0 < c < len(ms)]
            letter = [c for c in ok if ms[c - 1][0][0].lower() != ms[c][0][0].lower()]
            cut = min(letter or ok, key=lambda c: abs(c - len(ms) / 2))
            halves = [ms[:cut], ms[cut:]]
            z0, a1 = boundary(halves[0][-1][0], halves[1][0][0])
            labels = ["%s-%s" % (ms[0][0][0].upper(), z0), "%s-%s" % (a1, ms[-1][0][0].upper())]
        else:
            halves, labels = [ms, []], ["", ""]
        for h in range(2):
            part = halves[h]
            title = "%s %s" % (tname.upper(), labels[h]) if labels[h] else tname.upper() if h == 0 else "%s (unused)" % tname.upper()
            lists.append(dict(key="p_pick_%s_%d" % (slug(tname), h + 1), type=t, half=h, label=labels[h], title=title,
                              names=[m[0] for m in part], slots=[m[1] for m in part], presets=[m[2] for m in part]))
    return types, idx, count, lists


def list_params(types, lists):
    """The params.json entries for the lists, in their permanent order (after p_preset_next)."""
    out = [{"key": "p_list", "name": "PRESET LIST", "options": ["%s %d" % (types[l["type"]], l["half"] + 1) for l in lists],
            "default": "%s 1" % types[0]}]
    for l in lists:
        names = l["names"] or ["-"]
        names = names + [names[-1]] * (2 - len(names))   # an option list needs two entries; the skin draws no list for these
        out.append({"key": l["key"], "name": l["title"][:24], "options": names, "default": names[0], "refresh_display": True})
    out.append({"key": "p_index", "name": "PRESET NUMBER", "min": 0, "max": INDEX_MAX, "default": 0, "display": "int"})
    return out


def sync_params(path, wanted, write):
    """Checks (or rewrites) the list params in params.json, one per line as the file has them. -> True if in sync."""
    lines = open(path).read().split("\n")
    keys = [w["key"] for w in wanted]
    have = {}
    for n, line in enumerate(lines):
        m = re.match(r'\s*\{"key": "([^"]+)"', line)
        if m and m.group(1) in keys:
            have[m.group(1)] = n
    new = ["    " + json.dumps(w, ensure_ascii=False) for w in wanted]
    if [lines[have[k]].rstrip(",") if k in have else None for k in keys] == new:
        return True
    if not write:
        return False
    if have:   # they are the last params, in this order: replace them
        first, last = min(have.values()), max(have.values())
        if last - first + 1 != len(have) or len(have) != len(keys):
            raise SystemExit("gen_preset_types: params.json's list params are not one block of %d lines: fix by hand" % len(keys))
        lines[first:last + 1] = new
    else:      # append after the last param
        end = next(n for n, l in enumerate(lines) if l.strip() == "],")
        lines[end:end] = new
    end = next(n for n, l in enumerate(lines) if l.strip() == "],")
    start = next(n for n, l in enumerate(lines) if l.strip() == '"params": [')
    entries = [n for n in range(start + 1, end) if lines[n].strip()]   # (blank lines group the params)
    for n in entries:
        lines[n] = lines[n].rstrip(",") + ("," if n != entries[-1] else "")
    open(path, "w").write("\n".join(lines))
    json.load(open(path))   # still valid json
    print("gen_preset_types: updated the preset list params in params.json")
    return True


def c_arr(ctype, name, vals):
    return "static const %s %s[%d] = {%s};\n" % (ctype, name, len(vals), ", ".join(str(v) for v in vals))


def main():
    ppath = os.path.join(HERE, "params.json")
    d = json.load(open(ppath))
    params = {p["key"]: p for p in (d["params"] if isinstance(d, dict) else d)}
    presets = json.load(open(os.path.join(HERE, "presets.json")))["presets"]
    types, idx, count, lists = compute(params, presets)
    if not sync_params(ppath, list_params(types, lists), "--params" in sys.argv[1:]):
        raise SystemExit("gen_preset_types: the preset list params in params.json are out of date: "
                         "run python3 vst/gen_preset_types.py --params")
    list_of, opt_of, slot_of = [0] * len(presets), [0] * len(presets), [0] * len(presets)
    start, flat = [], []
    for k, l in enumerate(lists):
        start.append(len(flat))
        flat += l["slots"]
        for o, (s, p) in enumerate(zip(l["slots"], l["presets"])):
            list_of[p], opt_of[p], slot_of[p] = k, o, s
    out = os.path.join(HERE, "build", "preset_types.h")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    body = ("// Generated by vst/gen_preset_types.py from presets.json: do not edit.\n"
            "#pragma once\n"
            "#define PRESET_TYPES %d\n" % len(types)
            + c_arr("unsigned char", "PRESET_TYPE", idx)
            + c_arr("short", "PRESET_TYPE_COUNT", count)
            + "// The PRESETS page's name lists. List k is the param PRESET_LIST_KEY[k]; its option o is the preset in slot\n"
            "// PRESET_LIST_SLOT[PRESET_LIST_START[k] + o] (PRESET's value) of type PRESET_LIST_TYPE[k].\n"
            "#define PRESET_LISTS %d\n" % len(lists)
            + "static const char *const PRESET_LIST_KEY[%d] = {%s};\n" % (len(lists), ", ".join('"%s"' % l["key"] for l in lists))
            + c_arr("unsigned char", "PRESET_LIST_TYPE", [l["type"] for l in lists])
            + c_arr("short", "PRESET_LIST_COUNT", [len(l["names"]) for l in lists])
            + c_arr("short", "PRESET_LIST_START", start)
            + c_arr("short", "PRESET_LIST_SLOT", flat)
            + "// Per preset, in presets.json order: its list, its option in that list, its slot (PRESET's value) in its type.\n"
            + c_arr("unsigned char", "PRESET_LIST_OF", list_of)
            + c_arr("short", "PRESET_OPT_OF", opt_of)
            + c_arr("short", "PRESET_SLOT_OF", slot_of))
    if not os.path.exists(out) or open(out).read() != body:   # unchanged: leave the file alone, so nothing rebuilds
        open(out, "w").write(body)
    print("preset_types.h: %d presets in %d types (%s); %d name lists" % (
        len(idx), len(types), ", ".join("%s %d" % tc for tc in zip(types, count)), sum(1 for l in lists if len(l["names"]) > 1)))


if __name__ == "__main__":
    main()
