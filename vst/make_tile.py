#!/usr/bin/env python3
"""Draw the 270x110 Sounds > Instruments browser tile (vst/tile.png) in the skin's colours.

MPC shows a plugin in Sounds > INSTRUMENTS when its folder has Plugin Skins/browser_images/soundsmode.png, and tapping
the tile opens the plugin's preset page (its Presets/*.xpl, by category). vst/package_mpc.py ships vst/tile.png there.
Placeholder art: replace vst/tile.png with any 270x110 PNG.
"""
import os
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
W, H = 270, 110
PANEL, ACCENT, INK, DIM = (196, 194, 186), (122, 52, 32), (28, 28, 27), (69, 68, 63)   # layout.conf theme_*


def font(path, size, index=0):
    try:
        return ImageFont.truetype(path, size, index=index)
    except OSError:
        return ImageFont.load_default()


im = Image.new("RGB", (W, H), PANEL)
d = ImageDraw.Draw(im)
d.rectangle([0, 0, W - 1, H - 1], outline=(134, 132, 124), width=2)
d.rectangle([0, 0, 9, H - 1], fill=ACCENT)                          # the rust stripe of the panel
title = font("/System/Library/Fonts/Supplemental/DIN Condensed Bold.ttf", 46)
small = font("/System/Library/Fonts/Supplemental/DIN Alternate Bold.ttf", 13)
d.text((24, 18), "MILLSTONE", font=title, fill=INK)
d.text((26, 74), "8-VOICE HYBRID SYNTH", font=small, fill=DIM)
im.save(os.path.join(HERE, "tile.png"))
print("wrote vst/tile.png", im.size)
