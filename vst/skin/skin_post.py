#!/usr/bin/env python3
"""Touch-ups to the built skin's TUI.json that the layout syntax cannot say (vst.json "skin_post"; the port kit runs
`python3 vst/skin/skin_post.py <skin dir>` from vst/ after building the skin).

PRESETS page: a double tap on PRESET's text opens the name list that holds the current sound. The stepper's text is
copied once per list (vst/gen_preset_types.py), each copy shown only while p_list names its list
(IndexedEnabling, as a layout when= does), and the copy's double tap toggles that list's "open" flag (its "Open"
handle, as the kit's wheel=1 popup field does) instead of MPC's knob overlay. A single tap still gives PRESET the
focus, so the data wheel and Q-Links step it. Lists of one name (Init, unused halves) keep the knob overlay.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
VST = os.path.dirname(HERE)


def param_index():
    """key -> VST index, from the generated params.h (the layout's popup flags come after params.json's list)."""
    keys = re.findall(r'^\s*\{"([^"]+)", "', open(os.path.join(VST, "build", "params.h")).read(), re.M)
    return {k: i for i, k in enumerate(keys)}


def no_dupes(pairs):
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise SystemExit("skin_post: TUI.json has duplicate keys; cannot edit it with json")
    return dict(pairs)


def main(skin):
    path = os.path.join(skin, "Plugin Skins", "TUI.json")
    tui = json.load(open(path), object_pairs_hook=no_dupes)
    index = param_index()
    sys.path.insert(0, HERE)
    import pages
    _, lists = pages.preset_lists()
    li, pi = index["p_list"], index["p_preset"]
    local = tui["pageData"]["componentDefinitions"]["localComponentDefinitions"]
    defs = {d["key"]: d for d in local}
    page = next((d for k, d in defs.items() if k.startswith("PRESETS|")), None)
    if page is None:
        raise SystemExit("skin_post: no PRESETS page in TUI.json")
    kids = page["value"]["componentsData"]
    at = next((n for n, c in enumerate(kids) if c["componentData"]["type"].startswith("shStepText_")
               and {"key": "Data", "value": "Parameter %d" % pi} in c["handle remapping"]["map"]), None)
    if at is None:
        raise SystemExit("skin_post: PRESET's stepper text not found on the PRESETS page")
    text = kids[at]
    tdef = defs[text["componentData"]["type"]]
    lkey = text["componentData"]["type"].replace("shStepText_", "shStepTextList_", 1)
    ldef = json.loads(json.dumps(tdef))
    ldef["key"] = lkey
    actions = [a for a in ldef["value"]["actions"] if a["onAction"] != "Double Click"]
    actions.append({"version": 2, "onAction": "Double Click", "handler": "Toggle Switch", "handleName": "Open",
                    "additionalData": "", "handle remapping": {"version": 1, "map": []}})
    ldef["value"]["actions"] = actions
    local.append(ldef)
    copies, opened = [], 0
    for k, l in enumerate(lists):
        c = json.loads(json.dumps(text))
        c["componentData"]["name"] = "PRESET %s" % l["title"]
        c["bounds"]["showWhenDataModelInvalid"] = "Show"
        c["bounds"]["additionalInvalidatingHandles"] = c["bounds"]["additionalInvalidatingHandles"] + [
            "IndexedEnabling/%d/%d/Parameter %d" % (k, len(lists), li)]
        oi = index.get(l["key"] + "__open")
        if oi is not None and len(l["names"]) > 1:
            c["componentData"]["type"] = lkey
            c["handle remapping"]["map"].append({"key": "Open", "value": "Parameter %d" % oi})
            opened += 1
        copies.append(c)
    kids[at:at + 1] = copies
    out = json.dumps(tui, separators=(",", ":"))   # as the kit writes it (shadow_skin.write_skin)
    open(path, "w").write(out if len(out) > 8_000_000 else json.dumps(tui, indent=4))
    print("skin_post: PRESET's double tap opens %d name lists" % opened)


if __name__ == "__main__":
    main(sys.argv[1])
