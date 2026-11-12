#!/usr/bin/env python3
"""Check a packaged MPC plugin folder against Akai's MPC Plugin SDK rules (MPC OS 3.10.1+).

Mirrors the checks of the SDK's tools/validate.py (plugin-folder-format.md, ui-reference.md section 10):
folder name, plugin.json, ELF binaries (arch, libraries, glibc, VSTPluginMain the only export),
version.xml uiversion, TUI.json tabs and parameter handles, images, Q-Links.json. Standard library only.

    python3 tools/check_mpc_folder.py "dist/glaser - VST - Millstone" [--params vst/build/params.h]
"""

import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

ALLOWED_LIBS = {"libc.so.6", "libm.so.6", "libpthread.so.0", "libdl.so.2", "librt.so.1", "libgcc_s.so.1",
                "ld-linux-armhf.so.3", "ld-linux-aarch64.so.1"}
GLIBC_MAX, GLIBC_WARN = (2, 39), (2, 36)
ILLEGAL = '"#@,;:<>*^|?\\/'
PARAM_RE = re.compile(r"(?:^|/)Parameter (\d+)$")
IMG_KEYS = ("/filmStrip", "/image", "/onImage", "/offImage")

errors, warnings = [], []


def err(m): errors.append(m); print("ERROR  " + m)
def warn(m): warnings.append(m); print("warn   " + m)
def ok(m): print("ok     " + m)


def elf_info(path):
    d = open(path, "rb").read()
    if d[:4] != b"\x7fELF":
        raise ValueError("not an ELF file")
    is64, le = d[4] == 2, d[5] == 1
    e = "<" if le else ">"
    if is64:
        e_type, e_machine = struct.unpack_from(e + "HH", d, 16)
        shoff, = struct.unpack_from(e + "Q", d, 40)
        shentsize, shnum, shstrndx = struct.unpack_from(e + "HHH", d, 58)
    else:
        e_type, e_machine = struct.unpack_from(e + "HH", d, 16)
        shoff, = struct.unpack_from(e + "I", d, 32)
        shentsize, shnum, shstrndx = struct.unpack_from(e + "HHH", d, 46)
    secs = []
    for i in range(shnum):
        o = shoff + i * shentsize
        if is64:
            name, typ, _, _, off, size, link, _, _, entsize = struct.unpack_from(e + "IIQQQQIIQQ", d, o)
        else:
            name, typ, _, _, off, size, link, _, _, entsize = struct.unpack_from(e + "IIIIIIIIII", d, o)
        secs.append(dict(type=typ, off=off, size=size, link=link, entsize=entsize))

    def cstr(sec, i):
        s = secs[sec]["off"] + i
        return d[s:d.index(b"\0", s)].decode()

    needed, versions, exports = [], set(), []
    for s in secs:
        if s["type"] == 6:  # SHT_DYNAMIC
            step = 16 if is64 else 8
            for o in range(s["off"], s["off"] + s["size"], step):
                tag, val = struct.unpack_from(e + ("qQ" if is64 else "iI"), d, o)
                if tag == 0:
                    break
                if tag == 1:
                    needed.append(cstr(s["link"], val))
        elif s["type"] == 0x6FFFFFFE:  # SHT_GNU_verneed
            o = s["off"]
            while True:
                _, cnt, _, aux, nxt = struct.unpack_from(e + "HHIII", d, o)
                a = o + aux
                for _ in range(cnt):
                    _, _, _, vname, anext = struct.unpack_from(e + "IHHII", d, a)
                    versions.add(cstr(s["link"], vname))
                    a += anext
                if not nxt:
                    break
                o += nxt
        elif s["type"] == 11:  # SHT_DYNSYM
            n = s["size"] // s["entsize"]
            for i in range(1, n):
                o = s["off"] + i * s["entsize"]
                if is64:
                    nm, info, other, shndx = struct.unpack_from(e + "IBBH", d, o)
                else:
                    nm, _, _, info, other, shndx = struct.unpack_from(e + "IIIBBH", d, o)
                bind = info >> 4
                if shndx != 0 and bind in (1, 2) and (other & 3) == 0:
                    exports.append(cstr(s["link"], nm))
    return dict(is64=is64, type=e_type, machine=e_machine, needed=needed, versions=versions, exports=exports)


def vtuple(s):
    try:
        return tuple(int(x) for x in s.split("."))
    except ValueError:
        return None


def check_binary(path, want64, key):
    try:
        b = elf_info(path)
    except Exception as ex:  # noqa: BLE001
        return err("%s: %s" % (key, ex))
    if b["is64"] != want64:
        err("%s: is %d-bit, must be %d-bit" % (key, 64 if b["is64"] else 32, 64 if want64 else 32))
    if b["machine"] != (183 if want64 else 40):
        err("%s: wrong machine type %d" % (key, b["machine"]))
    if b["type"] != 3:
        err("%s: not a shared object" % key)
    bad = [l for l in b["needed"] if l not in ALLOWED_LIBS]
    (err if bad else ok)("%s: needed libraries %s" % (key, ", ".join(b["needed"])))
    gl = [vtuple(v[6:]) for v in b["versions"] if v.startswith("GLIBC_")]
    gl = max(g for g in gl if g) if gl else None
    if gl and gl > GLIBC_MAX:
        err("%s: needs GLIBC_%s > 2.39" % (key, ".".join(map(str, gl))))
    elif gl and gl > GLIBC_WARN:
        warn("%s: needs GLIBC_%s" % (key, ".".join(map(str, gl))))
    else:
        ok("%s: max GLIBC %s" % (key, ".".join(map(str, gl)) if gl else "none"))
    if any(v.startswith("GLIBCXX_") for v in b["versions"]):
        warn("%s: depends on the shared libstdc++; link it statically" % key)
    if "VSTPluginMain" not in b["exports"]:
        err("%s: VSTPluginMain not exported" % key)
    extra = [x for x in b["exports"] if x != "VSTPluginMain"]
    if extra:
        warn("%s: exports %d symbols besides VSTPluginMain (e.g. %s)" % (key, len(extra), ", ".join(extra[:5])))
    else:
        ok("%s: exports only VSTPluginMain" % key)


def walk(v, path=""):
    if isinstance(v, dict):
        for k, x in v.items():
            yield from walk(x, path + "/" + str(k))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            yield from walk(x, "%s[%d]" % (path, i))
    else:
        yield path, v


def main():
    args = sys.argv[1:]
    nparams = None
    if "--params" in args:
        i = args.index("--params")
        txt = open(args[i + 1]).read()
        m = re.search(r"#define\s+N_?PARAMS\s+(\d+)", txt) or re.search(r"NUM_PARAMS\s*=?\s*(\d+)", txt)
        nparams = int(m.group(1)) if m else None
        del args[i:i + 2]
    folder = args[0].rstrip("/")

    pj = json.load(open(os.path.join(folder, "plugin.json")))
    want = "".join(c for c in "%s - VST - %s" % (pj["manufacturer"], pj["name"]) if c not in ILLEGAL)
    (ok if os.path.basename(folder) == want else err)('folder name "%s" (must be "%s")' % (os.path.basename(folder), want))
    for k in ("name", "manufacturer", "version", "kind", "uid", "numInputs", "numOutputs", "file32", "file64"):
        if k not in pj:
            err("plugin.json missing %s" % k)
    if pj.get("format") != "vst2":
        warn('plugin.json format should be "vst2"')
    if pj.get("numOutputs", 0) <= 0:
        err("plugin.json numOutputs must be > 0")
    if not (isinstance(pj.get("uid"), str) and len(pj["uid"]) == 4):
        warn("uid is not a 4-char code")
    for key, w64 in (("file32", False), ("file64", True)):
        rel = pj.get(key)
        if not rel:
            continue
        p = os.path.realpath(os.path.join(folder, rel))
        if os.path.isabs(rel) or ".." in rel or not p.startswith(os.path.realpath(folder) + os.sep):
            err("%s path must be relative and inside the folder" % key)
        elif not os.path.isfile(p):
            err("%s: %s missing" % (key, rel))
        else:
            check_binary(p, w64, key)

    vx = os.path.join(folder, "version.xml")
    skins = os.path.join(folder, "Plugin Skins")
    if os.path.isfile(vx):
        r = ET.parse(vx).getroot()
        u = r.findtext("uiversion")
        if u is None:
            warn("version.xml has no <uiversion>")
        elif vtuple(u) is None or vtuple(u) + (0,) * (4 - len(vtuple(u))) > (0, 1, 0, 0):
            err("version.xml uiversion %s > 0.1.0.0: the MPC refuses the plugin" % u)
        else:
            ok("version.xml uiversion %s" % u)

    tui = json.load(open(os.path.join(skins, "TUI.json")))
    pd = tui.get("pageData", {})
    if pd.get("version") != 1:
        err("TUI.json pageData.version must be 1")
    tabs = pd.get("tabs", [])
    if len(tabs) > 32:
        err("TUI.json: %d tabs (max 32)" % len(tabs))
    seen, per_key = set(), {}
    for t in tabs:
        k = (t.get("fnKeyIndex"), t.get("fnKeySubIndex"))
        if k in seen:
            err("TUI.json: duplicate fnKey %s" % (k,))
        seen.add(k)
        per_key[k[0]] = per_key.get(k[0], 0) + 1
        if len(t.get("tabName", "")) > 8:
            warn('tab name "%s" longer than 8 characters' % t["tabName"])
    if any(n > 8 for n in per_key.values()):
        err("TUI.json: more than 8 sub-tabs on one function key %s" % per_key)
    ok("TUI.json: %d tabs on %d function keys %s" % (len(tabs), len(per_key), dict(sorted(per_key.items()))))
    hmax, imgs = -1, set()
    for path, v in walk(tui):
        if isinstance(v, str):
            m = PARAM_RE.search(v)
            if m:
                hmax = max(hmax, int(m.group(1)))
            if path.endswith(IMG_KEYS) and v:
                imgs.add(v)
    if nparams is not None:
        (err if hmax >= nparams else ok)("TUI.json: highest Parameter handle %d (plugin has %d)" % (hmax, nparams))
    missing = [i for i in imgs if not os.path.isfile(os.path.join(skins, i))]
    (err if missing else ok)("TUI.json: %d images referenced, %d missing %s" % (len(imgs), len(missing), missing[:5]))

    q = json.load(open(os.path.join(skins, "Q-Links.json")))
    if q.get("version") != 4 or q.get("Screen Mode Q-Links", {}).get("version") != 4:
        err("Q-Links.json versions must be 4")
    entries = q.get("Screen Mode Q-Links", {}).get("map", [])
    if len(entries) != len(tabs):
        warn("Q-Links.json has %d entries, TUI.json %d tabs" % (len(entries), len(tabs)))
    for e in entries:
        ql = e.get("Q-Links", {})
        if len(ql) != 16:
            err("Q-Links tab %s/%s: %d keys (need all 16)" % (e.get("Tab"), e.get("SubTab"), len(ql)))
        for k, v in ql.items():
            if nparams is not None and not (v == -1 or 0 <= v < nparams):
                err("Q-Links tab %s/%s %s = %s out of range" % (e.get("Tab"), e.get("SubTab"), k, v))
    if "Program Mode Q-Links" not in q:
        err("Q-Links.json has no Program Mode Q-Links")
    ok("Q-Links.json: %d tab entries" % len(entries))

    print("\n%d error(s), %d warning(s)" % (len(errors), len(warnings)))
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
