#!/usr/bin/env python3
"""Draw the skin's artwork with Pillow: the knob filmstrip and the cream panel plate.

    python3 vst/skin/make_art.py        -> vst/skin/knob.png, vst/skin/panel.png

Everything is drawn here (no photos). Lighting follows the port kit's "realistic hardware" notes
(docs/SKIN_STUDIO.md): one light from the top left that never moves. The knob's body (knurled rim, domed cap, sheen,
shadow) is drawn once and reused for every frame; only the pointer turns, so the highlight stays put as on a real knob.
"""
import math
import os
import random

from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SS = 4                   # supersampling for smooth edges
FRAMES = 64              # positions in the strip (the builder resamples to MPC's 128)
SIZE = 192               # one frame, px (64 x 192 = 12288 px tall, under MPC's 16384 limit)
LIGHT = -45              # degrees from the top, clockwise: top left
CREAM = (233, 225, 204)


def radial(size, inner, outer, cx, cy, r):
    """A radial gradient image (RGB), inner colour at (cx, cy) fading to outer at radius r."""
    im = Image.new("RGB", (size, size), outer)
    px = im.load()
    for y in range(size):
        for x in range(size):
            t = min(1.0, math.hypot(x - cx, y - cy) / r)
            t = t * t * (3 - 2 * t)
            px[x, y] = tuple(int(inner[i] + (outer[i] - inner[i]) * t) for i in range(3))
    return im


def knob_body(S):
    """The parts of the knob that do not turn, at S px (supersampled), on a transparent ground."""
    c = S / 2
    R = S * 0.40           # rim radius
    Rc = S * 0.31          # cap radius
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))

    # soft drop shadow, down-right, then a tight contact shadow
    sh = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sh).ellipse([c - R + S * 0.03, c - R + S * 0.05, c + R + S * 0.03, c + R + S * 0.05], fill=150)
    sh = sh.filter(ImageFilter.GaussianBlur(S * 0.035))
    out.paste((20, 16, 10, 255), (0, 0), sh)
    tight = Image.new("L", (S, S), 0)
    ImageDraw.Draw(tight).ellipse([c - R, c - R + S * 0.012, c + R, c + R + S * 0.012], fill=170)
    out.paste((10, 8, 5, 255), (0, 0), tight.filter(ImageFilter.GaussianBlur(S * 0.008)))

    # knurled rim: 40 ridges, each lit by how it faces the light
    d = ImageDraw.Draw(out)
    d.ellipse([c - R, c - R, c + R, c + R], fill=(22, 21, 20, 255))
    n = 40
    for k in range(n):
        a0 = 360.0 * k / n
        facing = math.cos(math.radians(a0 + 360.0 / n / 2 - LIGHT))
        v = int(30 + 34 * max(0.0, facing) + 6 * facing)
        pts = [(c, c)]
        for j in range(5):
            a = math.radians(a0 + 360.0 / n * 0.62 * j / 4 - 90)
            pts.append((c + R * math.cos(a), c + R * math.sin(a)))
        d.polygon(pts, fill=(v, v, v - 2, 255))
    # rim edge highlight on the lit side
    hl = Image.new("L", (S, S), 0)
    ImageDraw.Draw(hl).arc([c - R + 2, c - R + 2, c + R - 2, c + R - 2], 180, 290, fill=130, width=max(2, S // 90))
    out.paste((235, 232, 225, 255), (0, 0), hl.filter(ImageFilter.GaussianBlur(S * 0.004)))

    # the step down to the cap: a dark ring, shadow falling down-right
    d.ellipse([c - Rc - S * 0.02, c - Rc - S * 0.012, c + Rc + S * 0.025, c + Rc + S * 0.03], fill=(8, 8, 8, 255))

    # domed cap: radial gradient, highlight top left, darker far edge
    cap = radial(S, (78, 77, 75), (14, 14, 14), c - Rc * 0.45, c - Rc * 0.5, Rc * 1.55)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([c - Rc, c - Rc, c + Rc, c + Rc], fill=255)
    out.paste(cap, (0, 0), m)
    # fixed soft specular patch
    spec = Image.new("L", (S, S), 0)
    ImageDraw.Draw(spec).ellipse([c - Rc * 0.70, c - Rc * 0.78, c - Rc * 0.05, c - Rc * 0.25], fill=70)
    out.paste((255, 255, 255, 255), (0, 0), ImageChops.multiply(spec.filter(ImageFilter.GaussianBlur(S * 0.03)), m))
    return out


def pointer(S, deg):
    """The turning part: a white pointer line from the cap to the rim, with a dark edge."""
    c = S / 2
    lay = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    a = math.radians(deg - 90)
    r0, r1 = S * 0.12, S * 0.37
    p0 = (c + r0 * math.cos(a), c + r0 * math.sin(a))
    p1 = (c + r1 * math.cos(a), c + r1 * math.sin(a))
    d.line([p0, p1], fill=(0, 0, 0, 200), width=int(S * 0.05))
    d.line([p0, p1], fill=(246, 243, 236, 255), width=int(S * 0.028))
    return lay


def knob_strip():
    S = SIZE * SS
    body = knob_body(S)
    strip = Image.new("RGBA", (SIZE, SIZE * FRAMES), (0, 0, 0, 0))
    for f in range(FRAMES):
        deg = -135 + 270.0 * f / (FRAMES - 1)          # minimum first, 270 degrees of travel
        frame = Image.alpha_composite(body, pointer(S, deg)).resize((SIZE, SIZE), Image.LANCZOS)
        strip.paste(frame, (0, SIZE * f))
    path = os.path.join(HERE, "knob.png")
    strip.save(path, optimize=True)
    return path


def screw(S):
    """A slotted screw head, lit from the top left, on a transparent ground."""
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    c = S / 2
    r = S * 0.36
    sh = Image.new("L", (S, S), 0)
    ImageDraw.Draw(sh).ellipse([c - r + 2, c - r + 3, c + r + 2, c + r + 3], fill=140)
    im.paste((40, 32, 20, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(S * 0.05)))
    head = radial(S, (215, 212, 205), (95, 92, 86), c - r * 0.4, c - r * 0.45, r * 1.6)
    m = Image.new("L", (S, S), 0)
    ImageDraw.Draw(m).ellipse([c - r, c - r, c + r, c + r], fill=255)
    im.paste(head, (0, 0), m)
    d = ImageDraw.Draw(im)
    a = math.radians(28)
    dx, dy = r * 0.82 * math.cos(a), r * 0.82 * math.sin(a)
    d.line([(c - dx, c - dy), (c + dx, c + dy)], fill=(45, 43, 40, 255), width=max(2, int(S * 0.09)))
    d.line([(c - dx, c - dy + 2), (c + dx, c + dy + 2)], fill=(230, 228, 222, 120), width=max(1, int(S * 0.03)))
    return im


SWITCH_W, SWITCH_H = 72, 96   # the switch image with room for its shadow (pages.py places it at this size)


def slide_switch(on):
    """A black slide switch: slotted housing, ribbed slider down (off) or up (on), a red lamp when on.
    The switch itself is 48x72; the image is SWITCH_W x SWITCH_H so its shadow (down-right, like the knobs') can fade
    out instead of being cut off at the edge of a tight image."""
    W, H = 48, 72
    S = SS
    im = Image.new("RGBA", (W * S, H * S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([4 * S, 6 * S, 42 * S, 68 * S], radius=6 * S, fill=(26, 25, 24, 255))      # housing
    d.rounded_rectangle([4 * S, 6 * S, 42 * S, 68 * S], radius=6 * S, outline=(70, 68, 64, 255), width=S)
    d.rounded_rectangle([17 * S, 12 * S, 29 * S, 62 * S], radius=3 * S, fill=(6, 6, 6, 255))       # slot
    y0 = 13 if on else 37                                                                         # slider
    d.rounded_rectangle([9 * S, y0 * S, 37 * S, (y0 + 22) * S], radius=3 * S, fill=(44, 43, 41, 255))
    for k in range(5):                                                                            # ribs, lit on top
        yy = (y0 + 4 + 3.5 * k) * S
        d.line([(12 * S, yy), (34 * S, yy)], fill=(96, 94, 90, 255), width=S)
        d.line([(12 * S, yy + S), (34 * S, yy + S)], fill=(12, 12, 12, 255), width=S)
    d.line([(10 * S, (y0 + 0.5) * S), (36 * S, (y0 + 0.5) * S)], fill=(150, 148, 142, 255), width=S)
    lamp = (210, 40, 30, 255) if on else (70, 30, 26, 255)                                        # indicator
    d.ellipse([39 * S, 1 * S, 47 * S, 9 * S], fill=lamp)
    if on:
        g = Image.new("L", im.size, 0)
        ImageDraw.Draw(g).ellipse([36 * S, -2 * S, 50 * S, 12 * S], fill=120)
        im.paste((255, 90, 60, 255), (0, 0), g.filter(ImageFilter.GaussianBlur(2 * S)))
        d.ellipse([41 * S, 3 * S, 44 * S, 6 * S], fill=(255, 200, 180, 255))
    big = Image.new("RGBA", (SWITCH_W * S, SWITCH_H * S), (0, 0, 0, 0))
    ox, oy = (SWITCH_W - W) // 2 * S, (SWITCH_H - H) // 2 * S
    sh = Image.new("L", big.size, 0)                      # soft drop shadow, then a tight contact shadow
    ImageDraw.Draw(sh).rounded_rectangle([ox + 8 * S, oy + 12 * S, ox + 46 * S, oy + 74 * S], radius=7 * S, fill=125)
    big.paste((40, 30, 15, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur(4 * S)))
    ct = Image.new("L", big.size, 0)
    ImageDraw.Draw(ct).rounded_rectangle([ox + 5 * S, oy + 8 * S, ox + 43 * S, oy + 70 * S], radius=6 * S, fill=150)
    big.paste((20, 15, 8, 255), (0, 0), ct.filter(ImageFilter.GaussianBlur(1 * S)))
    big.alpha_composite(im, (ox, oy))
    out = big.resize((SWITCH_W, SWITCH_H), Image.LANCZOS)
    path = os.path.join(HERE, "switch_%s.png" % ("on" if on else "off"))
    out.save(path, optimize=True)
    return path


BUTTON_W, BUTTON_H = 80, 76   # a 56x52 cap plus room for its shadow (pages.py places buttons at this size)


def cap_button(pressed):
    """A dark square push cap, lit from the top left: soft shadow down-right, a light top edge, a darker bottom edge.
    Pressed, it sits lower: a shorter shadow and a darker face. The renderer prints the label (- / +) on top."""
    S = SS
    big = Image.new("RGBA", (BUTTON_W * S, BUTTON_H * S), (0, 0, 0, 0))
    x0, y0 = (BUTTON_W - 56) // 2 * S, (BUTTON_H - 52) // 2 * S
    x1, y1 = x0 + 56 * S, y0 + 52 * S
    lift = 1 if pressed else 4
    sh = Image.new("L", big.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle([x0 + lift * S, y0 + (lift + 2) * S, x1 + lift * S, y1 + (lift + 2) * S], radius=8 * S, fill=130)
    big.paste((40, 30, 15, 255), (0, 0), sh.filter(ImageFilter.GaussianBlur((2 if pressed else 4) * S)))
    d = ImageDraw.Draw(big)
    face = (30, 27, 24, 255) if pressed else (44, 40, 36, 255)
    d.rounded_rectangle([x0, y0, x1, y1], radius=8 * S, fill=(14, 12, 10, 255))               # rim
    d.rounded_rectangle([x0 + 2 * S, y0 + 2 * S, x1 - 2 * S, y1 - 2 * S], radius=7 * S, fill=face)
    if not pressed:                                                                           # lit top, dark bottom
        d.line([(x0 + 8 * S, y0 + 3 * S), (x1 - 8 * S, y0 + 3 * S)], fill=(120, 114, 106, 255), width=S)
        d.line([(x0 + 8 * S, y1 - 3 * S), (x1 - 8 * S, y1 - 3 * S)], fill=(10, 9, 8, 255), width=S)
    out = big.resize((BUTTON_W, BUTTON_H), Image.LANCZOS)
    path = os.path.join(HERE, "button_%s.png" % ("on" if pressed else "off"))
    out.save(path, optimize=True)
    return path


WOOD = 18                # px of wood side cheek, each side


def wood(w, h, mirror=False, seed=0):
    """A walnut side cheek: long vertical grain with a few wavy streaks, rounded by light from the left."""
    rnd = random.Random(seed + 11)
    im = Image.new("RGB", (w * SS, h), (92, 56, 34))
    px = im.load()
    streaks = [(rnd.uniform(0, w * SS), rnd.uniform(0.6, 2.2), rnd.uniform(0, 6.28), rnd.uniform(-22, 22)) for _ in range(26)]
    for y in range(h):
        for x in range(w * SS):
            v = 0.0
            for sx, amp, ph, dv in streaks:
                dx = x - (sx + amp * SS * math.sin(y / 37.0 + ph) + 1.5 * SS * math.sin(y / 211.0 + ph * 2))
                v += dv * math.exp(-(dx * dx) / (2.0 * (0.9 * SS) ** 2))
            u = x / (w * SS - 1)                                  # across the cheek: rounded, lit from the left
            if mirror:
                u = 1 - u
            shade = 0.78 + 0.34 * math.sin(math.pi * (0.15 + 0.7 * u)) - 0.12 * u
            r, g, b = 92 + v, 56 + v * 0.62, 34 + v * 0.38
            px[x, y] = (int(max(0, min(255, r * shade))), int(max(0, min(255, g * shade))), int(max(0, min(255, b * shade))))
    im = im.resize((w, h), Image.LANCZOS)
    noise = Image.effect_noise((w, h), 10)
    return ImageChops.add(im, Image.merge("RGB", [noise.point(lambda v: (v - 128) // 8 + 128)] * 3), 1.0, -128)


def panel():
    """The 1280x628 plate: cream face, top-left light, fine grain, a bevelled edge and four screws."""
    W, H = 1280, 628
    rnd = random.Random(7)
    gx = Image.linear_gradient("L").rotate(90).resize((W, H))      # light falls from left to right
    gy = Image.linear_gradient("L").resize((W, H))                 # and from top to bottom
    light = ImageChops.add(gx, gy, 2.0)                            # diagonal, as the kit notes suggest
    face = Image.new("RGB", (W, H), CREAM)
    dark = Image.new("RGB", (W, H), (214, 204, 180))
    face = Image.composite(dark, face, light.point(lambda v: int(v * 0.55)))
    # grain
    noise = Image.effect_noise((W, H), 18).filter(ImageFilter.GaussianBlur(0.6))
    face = ImageChops.add(face, Image.merge("RGB", [noise.point(lambda v: (v - 128) // 6 + 128)] * 3), 1.0, -128)
    # vignette
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).rectangle([0, 0, W, H], outline=255, width=60)
    face = Image.composite(Image.new("RGB", (W, H), (196, 186, 162)), face, vig.filter(ImageFilter.GaussianBlur(40)).point(lambda v: v // 3))
    d = ImageDraw.Draw(face)
    # bevel: bright top-left edge, dark bottom-right edge
    for i in range(6):
        k = 1 - i / 6
        d.line([(i, i), (W - 1 - i, i)], fill=tuple(min(255, int(v + 30 * k)) for v in CREAM))
        d.line([(i, i), (i, H - 1 - i)], fill=tuple(min(255, int(v + 22 * k)) for v in CREAM))
        d.line([(i, H - 1 - i), (W - 1 - i, H - 1 - i)], fill=tuple(int(v * (0.70 + 0.3 * (1 - k))) for v in CREAM))
        d.line([(W - 1 - i, i), (W - 1 - i, H - 1 - i)], fill=tuple(int(v * (0.76 + 0.24 * (1 - k))) for v in CREAM))
    # wood side cheeks, left and right, over the plate's edge
    for x0 in (0, W - WOOD):
        cheek = wood(WOOD, H, mirror=x0 > 0, seed=x0)
        face.paste(cheek, (x0, 0))
        # the plate's edge casts a thin shadow onto it, and the cheek's own inner edge catches light
        edge = WOOD if x0 == 0 else x0 - 1
        d.line([(edge, 0), (edge, H)], fill=(60, 45, 30))
        d.line([(edge + (1 if x0 == 0 else -1), 0), (edge + (1 if x0 == 0 else -1), H)], fill=(120, 108, 88))
    sc = screw(24 * SS).resize((24, 24), Image.LANCZOS)
    for x, y in ((WOOD + 5, 5), (W - WOOD - 29, 5), (WOOD + 5, H - 29), (W - WOOD - 29, H - 29)):   # corners, outside the frames
        face.paste(sc, (x, y), sc)
    path = os.path.join(HERE, "panel.png")
    face.save(path, optimize=True)
    return path


if __name__ == "__main__":
    print("wrote", knob_strip())
    print("wrote", panel())
    print("wrote", slide_switch(False))
    print("wrote", slide_switch(True))
    print("wrote", cap_button(False))
    print("wrote", cap_button(True))
