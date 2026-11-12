#!/usr/bin/env python3
"""Write the pages ([tab ...] sections) of vst/layout.conf from one grid, so every page lines up the same way.

    python3 vst/skin/pages.py vst/layout.conf      # replaces everything from the first [tab line on

The top of layout.conf (theme, art_css, knob strip, qlinks_track) is kept; each tab's qlinks line is carried over
from the current file (keys only change here if the page changes).

Coordinates are the layout's (shadow) ones: the plugin area is x 0..1280, y 86..714. Wood cheeks and screws take the
outer ~50 px of each side, so frames run x 52..1228. Knob geometry, as the skin builder places it (shadow_skin.py,
label_scale 1.25, scale_names on): the name sits r+2 below the centre (35 px), the value field under it (32 px), so a
knob needs r above and r+77 below its centre, and at least 162 px of width for its text. MPC's 16384 px image limit
caps r at 59.
"""
import re
import sys

X0, X1 = 52, 1228            # frame area, left to right
Y0, Y1 = 96, 704             # frame area, top to bottom
TITLE = 58                   # a frame's title band: first label row starts this far below its top
GAP = 16                     # between frames
PLATE = 'art file="skin/panel.png" x=0 y=86 w=1280 h=628 fit=stretch'

out = []


def frame(x0, y0, x1, y1, title):
    out.append('frame x=%d y=%d w=%d h=%d title="%s"' % (x0, y0, x1 - x0, y1 - y0, title))


RMAX = 54   # r=59 sits exactly on MPC's 16384 px filmstrip limit and garbled on the device (Key 37 G2, 2026-11-12)
NAME = 2.0  # baked knob/switch names (text size, about 10 px per 1.0)
VALUE = 34  # live value under a knob, px (MPC draws its font small: 28 read like the printed names)


def knob(cx, cy, r, label, key, bw=None, extra=""):
    """A knob whose name is printed into the panel (MPC's live name would be the long parameter name, e.g.
    "OSC1 HARMONICS"); the live value sits under the printed name (vy pushes it down)."""
    r = min(r, RMAX)
    if label and "ns=0" not in extra:
        size = NAME
        m = re.search(r"\bns=(\d+)", extra)
        if m:                                    # a narrow row asked for smaller names: print them smaller
            size = int(m.group(1)) / 11.0
            extra = extra.replace(m.group(0), "")
        out.append('text cx=%d cy=%d label="%s" size=%g color=1d1a16' % (cx, cy + r + 20, label, size))
        extra = " ns=0 vy=36" + extra
    if "vs=" not in extra:
        extra += " vs=%d" % VALUE                # the live value, bigger than the builder's default
    out.append('knob cx=%d cy=%d r=%d label="%s" key=%s%s%s' % (cx, cy, r, label, key, " bw=%d" % bw if bw else "", extra))


POP_TEXT = " tsize=%d tweight=bold tcolor=1d1a16"   # the value MPC draws in a field: bigger, bold, dark on the grey


def popup(cx, cy, w, label, key, h=52, extra=""):
    ts = 24 if h >= 50 else 21
    out.append('popup cx=%d cy=%d w=%d h=%d label="%s" key=%s%s%s' % (cx, cy, w, h, label, key, POP_TEXT % ts, extra))


def seg(cx, cy, label, key, sw, extra=""):
    out.append('enum_h cx=%d cy=%d sw=%d label="%s" key=%s%s' % (cx, cy, sw, label, key, extra))


def toggle(cx, cy, label, key):
    # the image is 72x96 (the switch 48x72 plus room for its shadow), centred on the switch itself
    out.append('toggle cx=%d cy=%d w=72 h=96 label="%s" key=%s ns=0' % (cx, cy, label, key))
    out.append('text cx=%d cy=%d label="%s" size=%g color=1d1a16' % (cx, cy + 54, label, NAME))


def button(cx, cy, label, key):
    out.append('button cx=%d cy=%d w=80 h=76 label="%s" key=%s' % (cx, cy, label, key))   # 56x52 cap + shadow room


def text(cx, cy, label, size=1.5, color="1d1a16"):
    out.append('text cx=%d cy=%d label="%s" size=%g color=%s' % (cx, cy, label, size, color))


def spread(x0, x1, n):
    """n centres spread evenly over x0..x1, each in the middle of its own equal cell."""
    step = (x1 - x0) / n
    return [round(x0 + step * (i + 0.5)) for i in range(n)]


def tab(name):
    out.append("")
    out.append("[tab %s]" % name)
    out.append(PLATE)


# ---------------------------------------------------------------------------------------------------------------
def osc(n, with_type):
    p = "o%d_" % n
    tab("OSC %d" % n)
    LX1 = 772                                    # oscillator frame | pitch/out frame
    frame(X0, Y0, LX1, Y1, "OSCILLATOR %d" % n)
    c = spread(X0, LX1, 3)                       # three columns: 172, 412, 652
    toggle(X0 + 56, 186, "ON", p + "on")
    button(196, 186, "-", p + "prev")
    popup(380, 186, 280, "MODEL", p + "engine", extra=" cols=3 cw=240")
    button(564, 186, "+", p + "next")
    if with_type:
        popup(LX1 - 82, 186, 130, "TYPE", p + "type")
    for cx, (lab, key) in zip(c, (("HARMONICS", "harm"), ("TIMBRE", "timbre"), ("MORPH", "morph"))):
        knob(cx, 330, 59, lab, p + key)
    for cx, (lab, key) in zip(spread(X0, LX1 - 150, 3), (("FM (ENV)", "fm"), ("TIMBRE CV", "timbre_mod"), ("MORPH CV", "morph_mod"))):
        knob(cx, 568, 44, lab, p + key, bw=170)
    popup(LX1 - 82, 568, 130, "CV SOURCE", p + "cv_src")
    frame(LX1 + GAP, Y0, X1, Y1, "PITCH / OUT")
    c2 = spread(LX1 + GAP, X1, 2)
    knob(c2[0], 206, 42, "OCTAVE", p + "oct")
    knob(c2[1], 206, 42, "SEMI", p + "semi")
    knob(c2[0], 390, 42, "FINE", p + "fine")
    knob(c2[1], 390, 42, "LEVEL", p + "level")
    knob(c2[0], 572, 40, "VC MIX", p + "mix")
    popup(c2[1], 572, 170, "AMP", p + "amp")


def filter_vca():
    tab("FILTER / VCA")
    LX1 = 816
    frame(X0, Y0, LX1, Y1, "VCF  24 dB LADDER")
    # a pyramid: CUTOFF on top in the middle and clearly the biggest, RESONANCE and DRIVE flanking it lower down
    mid = (X0 + LX1) // 2
    knob(mid, 248, 54, "CUTOFF", "cutoff")
    knob(mid - 236, 330, 40, "RESONANCE", "reso")
    knob(mid + 236, 330, 40, "DRIVE", "drive")
    c = spread(X0, LX1, 4)
    knob(c[0], 566, 36, "MOD DEPTH", "f_mod")
    popup(c[1], 552, 170, "MOD SOURCE", "f_src")
    knob(c[2], 566, 36, "KEY TRACK", "keytrack")
    popup(c[3], 552, 130, "MODE", "f_mode")
    frame(LX1 + GAP, Y0, X1, Y1, "VCA")
    c2 = spread(LX1 + GAP, X1, 2)
    popup((LX1 + GAP + X1) // 2, 186, 220, "MODE", "vca_mode")
    knob((LX1 + GAP + X1) // 2, 340, 59, "VOLUME", "volume")
    knob(c2[0], 580, 44, "VEL > AMP", "vel_amp")
    knob(c2[1], 580, 44, "VEL > VCF", "vel_filt")


def envelopes():
    tab("ENVELOPES")
    mid = (Y0 + Y1) // 2
    for (y0, y1, title, pre) in ((Y0, mid - GAP // 2, "VCA ENVELOPE  (ADSR)", ""), (mid + GAP // 2, Y1, "MOD ENVELOPE  (ADSR)", "m_")):
        frame(X0, y0, X1, y1, title)
        for cx, (lab, key) in zip(spread(X0, X1, 4), (("ATTACK", "attack"), ("DECAY", "decay"), ("SUSTAIN", "sustain"), ("RELEASE", "release"))):
            knob(cx, y0 + 108, 50, lab, pre + key)


def lfo_voice():
    tab("LFO / VOICE")
    LX1 = 760
    vy1 = 404
    frame(X0, Y0, LX1, vy1, "VOICE")
    popup(X0 + 150, 182, 220, "MODE", "voice_mode")
    c = spread(X0, LX1, 4)
    for cx, (lab, key) in zip(c, (("VOICES", "voices"), ("GLIDE", "glide"), ("OSC MOD", "vibrato"), ("NOISE", "noise"))):
        knob(cx, 290, 36, lab, key, bw=170)
    frame(X0, vy1 + GAP, LX1, Y1, "PRESSURE / LPG")
    c = spread(X0, LX1, 5)
    for cx, (lab, key) in zip(c, (("AT>CUT", "at_cutoff"), ("AT>MORPH", "at_morph"), ("LPG DECAY", "lpg_decay"),
                                  ("LPG COLOR", "lpg_colour"), ("BEND", "bend_range"))):
        knob(cx, vy1 + GAP + 110, 36, lab, key, bw=140, extra=" ns=21")
    frame(LX1 + GAP, Y0, X1, Y1, "LFO")
    c2 = spread(LX1 + GAP, X1, 2)
    cxm = (LX1 + GAP + X1) // 2
    popup(c2[0], 186, 170, "SHAPE", "lfo_shape")
    toggle(c2[1], 170, "SYNC", "lfo_sync")              # stacked, a switch plus its printed name apart (130 px)
    toggle(c2[1], 300, "RETRIG", "lfo_retrig")
    knob(c2[0], 350, 54, "RATE", "lfo_rate", extra=" when=lfo_sync:OFF")
    popup(c2[0], 320, 200, "DIVISION", "lfo_div", extra=" when=lfo_sync:ON")
    popup(c2[0], 430, 200, "PHASE", "lfo_lock", extra=" when=lfo_sync:ON")
    knob(c2[0], 575, 36, "WHEEL>LFO", "wheel_lfo")
    knob(c2[1], 575, 36, "AT>LFO", "at_lfo")


def matrix(first):
    tab("MOD MATRIX %d-%d" % (first, first + 5))
    frame(X0, Y0, X1, Y1, "MOD MATRIX %d-%d" % (first, first + 5))
    xs = (X0 + 40, 330, 770, 1110)               # number, FROM, TO, AMOUNT
    hy = 152
    text(xs[1], hy, "FROM", 1.5, "4a443b")
    text(xs[2], hy, "TO", 1.5, "4a443b")
    text(xs[3], hy, "AMOUNT", 1.5, "4a443b")
    for i in range(6):
        c = first + i
        cy = 200 + 88 * i
        text(xs[0], cy, str(c), 1.9, "7a2b20")
        popup(xs[1], cy, 400, "", "c%d_src" % c, h=50, extra=" cols=4 cw=130")
        popup(xs[2], cy, 400, "", "c%d_dst" % c, h=50, extra=" cols=6 cw=130")
        knob(xs[3], cy, 26, "", "c%d_amt" % c, extra=" ns=0 lay=side bw=180 bh=56 vs=26")


def lfo2():
    tab("LFO 2")
    frame(X0, Y0, X1, Y1, "LFO 2")
    c = spread(X0, X1, 3)
    popup(c[0], 200, 260, "SHAPE", "lfo2_shape")
    toggle(c[1], 190, "SYNC", "lfo2_sync")
    toggle(c[2], 190, "RETRIG", "lfo2_retrig")
    knob(c[1], 440, 54, "RATE", "lfo2_rate", extra=" when=lfo2_sync:OFF")
    popup(c[1], 400, 260, "DIVISION", "lfo2_div", extra=" when=lfo2_sync:ON")
    popup(c[1], 520, 260, "PHASE", "lfo2_lock", extra=" when=lfo2_sync:ON")


def tides():
    tab("TIDES")
    frame(X0, Y0, X1, Y1, "TIDES  (PATCH BAY SOURCE)")
    c = spread(X0, X1, 4)
    popup(c[0], 200, 200, "MODE", "t_mode")
    popup(c[1], 200, 200, "OUTPUT", "t_out")
    popup(c[2], 200, 200, "TRIGGER", "t_trig")
    popup(c[3], 200, 200, "DIV", "t_div")
    for cx, (lab, key) in zip(spread(X0, X1, 5), (("RATE", "t_rate"), ("SHAPE", "t_shape"), ("SLOPE", "t_slope"),
                                                   ("SMOOTH", "t_smooth"), ("SHIFT", "t_shift"))):
        knob(cx, 440, 59, lab, key)


def elements():
    tab("ELEMENTS")
    LX1 = 704
    frame(X0, Y0, LX1, Y1, "EXCITER")
    c = spread(X0, LX1, 3)
    grid = ((("BOW", "e_bow"), ("BLOW", "e_blow"), ("STRIKE", "e_strike")),
            (("BOW TMB", "e_bow_t"), ("BLOW TMB", "e_blow_t"), ("STRK TMB", "e_strike_t")),
            (("CONTOUR", "e_contour"), ("FLOW", "e_flow"), ("MALLET", "e_mallet")))
    for row, cy in zip(grid, (196, 368, 540)):
        for cx, (lab, key) in zip(c, row):
            knob(cx, cy, 40, lab, key)
    frame(LX1 + GAP, Y0, X1, Y1, "RESONATOR")
    c2 = spread(LX1 + GAP, X1, 3)
    popup(c2[0], 186, 160, "MODEL", "e_model")
    text(c2[0], 252, "OSC 1 TYPE", 1.2, "4a443b")
    text(c2[0], 276, "= ELEMENTS", 1.2, "4a443b")
    for (cx, cy), (lab, key) in zip(((c2[1], 210), (c2[2], 210), (c2[0], 430), (c2[1], 430), (c2[2], 430)),
                                    (("GEOMETRY", "e_geom"), ("BRIGHT", "e_bright"), ("DAMPING", "e_damp"),
                                     ("POSITION", "e_pos"), ("SPACE", "e_space"))):
        knob(cx, cy, 46, lab, key)


def phaser():
    tab("PHASER")
    frame(X0, Y0, X1, Y1, "PHASER")
    for cx, (lab, key) in zip(spread(X0, X1, 4), (("RATE", "fx_ph_rate"), ("DEPTH", "fx_ph_depth"),
                                                   ("FEEDBACK", "fx_ph_fb"), ("MIX", "fx_ph_mix"))):
        knob(cx, 360, 59, lab, key)


def chorus():
    tab("CHORUS")
    frame(X0, Y0, X1, Y1, "CHORUS")
    c = spread(X0, X1, 3)
    popup(c[0] + 60, 330, 260, "MODE", "fx_ch_mode")
    knob(c[1] + 60, 350, 59, "MIX", "fx_ch_mix")


def tape_delay():
    tab("TAPE DELAY")
    frame(X0, Y0, X1, Y1, "TAPE DELAY")
    c = spread(X0, X1, 5)
    toggle(c[0], 186, "SYNC", "fx_dl_sync")
    popup(c[1], 196, 170, "INPUT", "fx_dl_in")
    toggle(c[2], 186, "THROW", "fx_dl_throw")
    toggle(c[3], 186, "PING PONG", "fx_dl_pp")
    popup(c[4], 196, 170, "HEADS", "fx_dl_heads", extra=" cols=4 cw=90")
    knob(c[0], 350, 46, "TIME", "fx_dl_time", extra=" when=fx_dl_sync:FREE")
    popup(c[0], 330, 180, "DIV", "fx_dl_div", extra=" when=fx_dl_sync:SYNC cols=4 cw=100")
    for cx, (lab, key) in zip(c[1:], (("REPEATS", "fx_dl_fb"), ("MIX", "fx_dl_mix"), ("WIDTH", "fx_dl_width"), ("DRIVE", "fx_dl_drive"))):
        knob(cx, 350, 46, lab, key)
    for cx, (lab, key) in zip(spread(X0 + 120, X1 - 120, 4), (("LOW CUT", "fx_dl_low"), ("HIGH CUT", "fx_dl_high"),
                                                               ("WOW", "fx_dl_wow"), ("DUCK", "fx_dl_duck"))):
        knob(cx, 560, 46, lab, key)


def reverb():
    tab("REVERB")
    frame(X0, Y0, X1, Y1, "REVERB / OUTPUT")
    c = spread(X0, X1, 5)
    popup(c[0], 200, 200, "TYPE", "fx_rv_type")
    toggle(c[2], 200, "SPRING KICK", "fx_rv_kick")
    for cx, (lab, key) in zip(c, (("DECAY", "fx_rv_decay"), ("DIFFUSION", "fx_rv_diff"), ("DAMPING", "fx_rv_damp"),
                                  ("MIX", "fx_rv_mix"), ("OUTPUT dB", "fx_out"))):
        knob(cx, 420, 59, lab, key)


CLOCK_ROWS = (("SHAPE", "shape"), ("WIDTH", "width"), ("SWING", "swing"), ("PROB", "prob"), ("PHASE", "phase")), \
             (("LEVEL", "level"), ("OFFS", "offset"), ("STEPS", "steps"), ("FILL", "fill"), ("ROT", "rot"))


def clocks(first):
    """Two Euclidean clocks per page, each in its own frame: DIV on the left, its ten knobs in two rows."""
    tab("CLOCK %d-%d" % (first, first + 1))
    mid = (Y0 + Y1) // 2
    LCOL = 250                                   # left column (title, DIV) | knob area
    xs = spread(LCOL, X1, 5)
    for n, (y0, y1) in enumerate(((Y0, mid - 4), (mid + 4, Y1))):
        k = first + n
        frame(X0, y0, X1, y1, "CLOCK %d" % k)
        popup((X0 + LCOL) // 2, y0 + 112, 150, "DIV", "k%d_div" % k, h=46, extra=" cols=3 cw=100")
        if first == 1 and n == 0:                # the clocks' common source and tempo, on the first page
            popup((X0 + LCOL) // 2, y0 + 220, 150, "SRC (ALL)", "ck_src", h=46)
        if first == 1 and n == 1:
            text((X0 + LCOL) // 2, y0 + 184, "BPM (ALL)", 1.6, "1d1a16")
            knob((X0 + LCOL) // 2 + 20, y0 + 228, 18, "", "ck_bpm", extra=" ns=0 lay=side bw=150 bh=44 vs=26")
        for row, cy in zip(CLOCK_ROWS, (y0 + 64, y0 + 194)):
            for x, (lab, key) in zip(xs, row):
                knob(x, cy, 28, lab, "k%d_%s" % (k, key), bw=180)
    keys = []
    for k in (first, first + 1):                 # 16 Q-Links: per clock the four most turned, then four more
        keys += ["k%d_%s" % (k, x) for x in ("steps", "fill", "rot", "div", "level", "prob", "swing", "shape")]
    out.append('qlinks "CLK %d-%d" = %s' % (first, first + 1, ",".join(keys)))


def presets():
    tab("PRESETS")
    frame(X0, Y0, X1, Y1, "PRESETS")
    popup(640, 236, 560, "TYPE", "p_type", h=66, extra=" cols=2 cw=300")
    out.append('stepper cx=640 cy=440 w=1000 h=92 label="PRESET" key=p_preset tsize=44 tweight=bold tcolor=1d1a16')
    text(640, 600, "TYPE PICKS A CATEGORY, - / + STEP THROUGH IT. EVERY STEP LOADS THE SOUND.", 1.4, "4a443b")
    text(640, 636, "YOUR OWN SOUNDS: THE SAVE / LOAD ICONS AT THE TOP RIGHT.", 1.4, "4a443b")


PAGES = [lambda: osc(1, True), lambda: osc(2, False), lambda: osc(3, False), filter_vca, envelopes, lfo_voice,
         lambda: matrix(1), lambda: matrix(7), lfo2, tides, elements, phaser, chorus, tape_delay, reverb,
         lambda: clocks(1), lambda: clocks(3), lambda: clocks(5), lambda: clocks(7), presets]


def main(path):
    src = open(path).read()
    head, _, body = src.partition("\n[tab ")
    body = "[tab " + body
    qlinks = {}
    for t in re.split(r"\n(?=\[tab )", body):
        name = t.split("]", 1)[0][5:]
        qlinks[name] = [l for l in t.split("\n") if l.startswith("qlinks ")]
    for page in PAGES:
        start = len(out)
        page()
        name = out[start + 1][5:-1]
        if not any(l.startswith("qlinks ") for l in out[start:]):
            out.extend(qlinks.get(name, []))
    open(path, "w").write(head.rstrip("\n") + "\n" + "\n".join(out) + "\n")
    print("wrote %d pages into %s" % (len(PAGES), path))


if __name__ == "__main__":
    main(sys.argv[1])
