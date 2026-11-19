#!/usr/bin/env python3
"""Build the NEW bronze-CRT trading-terminal idle/win strips from the 96-frame atlas.

The 96-frame atlas (12 cols x 8 rows, 320x320 cells, left->right top->bottom) is a
continuous scrolling-chart loop on an already-transparent background. A full 96-frame
horizontal strip (~28,800px) would exceed the WebGL max texture width, so we subsample
to 48 frames (stride 2 -> still a clean loop) at full resolution (~14.4k strip).

We DON'T use tools/slice_sheet.py here because its "saturated body" centroid logic
treats the orange/bronze casing as flame (r>150,g>110,b<120) and would mis-anchor /
mis-scale the symbol. The casing is already pre-aligned per cell, so we only need:
alpha-clean each frame, crop all to a shared alpha-union window, and lay them out.

Writes (the game auto-loads both on refresh):
  public/symbols/anim/terminal_idle.{png,json}
  public/symbols/anim/terminal_win.{png,json}
"""
import importlib.util
import json
import os

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# reuse the proven alpha cleaner (kills faint dark halo, keeps the art)
spec = importlib.util.spec_from_file_location("ss", os.path.join(HERE, "slice_sheet.py"))
ss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ss)

ATLAS = os.path.join(ROOT, "sheets", "terminal", "trading_terminal_96f_atlas.png")
COLS, ROWS = 12, 8
STRIDE = 2            # 96 -> 48 frames (clean loop, strip stays < 16384px)
PAD = 6
IDLE_FPS = 16        # 48 frames -> 3.0s loop (smooth scrolling chart)
WIN_FPS = 20         # a touch snappier on a win


def cells(atlas):
    w, h = atlas.size
    cw, ch = w // COLS, h // ROWS
    for i in range(0, COLS * ROWS, STRIDE):
        r, c = divmod(i, COLS)
        yield atlas.crop((c * cw, r * ch, c * cw + cw, r * ch + ch))


def build():
    atlas = Image.open(ATLAS).convert("RGBA")
    frames = [ss._clean(cell.copy()) for cell in cells(atlas)]
    print(f"cut + cleaned {len(frames)} frames")

    # shared window = union of every frame's alpha bounding box (keeps the casing
    # perfectly still: every frame is cropped to the SAME rectangle, no re-centering)
    boxes = [f.split()[3].getbbox() or (0, 0, f.width, f.height) for f in frames]
    ux0 = max(0, min(b[0] for b in boxes) - PAD)
    uy0 = max(0, min(b[1] for b in boxes) - PAD)
    ux1 = min(frames[0].width, max(b[2] for b in boxes) + PAD)
    uy1 = min(frames[0].height, max(b[3] for b in boxes) + PAD)
    cw, ch = ux1 - ux0, uy1 - uy0
    print(f"union window {cw}x{ch} -> strip width {cw * len(frames)} (limit 16384)")
    assert cw * len(frames) <= 16384, "strip too wide for WebGL — raise STRIDE"

    strip = Image.new("RGBA", (cw * len(frames), ch), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        strip.paste(f.crop((ux0, uy0, ux1, uy1)), (i * cw, 0))

    out = os.path.join(ROOT, "public", "symbols", "anim")
    os.makedirs(out, exist_ok=True)
    for kind, fps in (("idle", IDLE_FPS), ("win", WIN_FPS)):
        strip.save(os.path.join(out, f"terminal_{kind}.png"))
        # whole-frame scaling (anchor centred); omit bodyFrac so the game sizes the
        # full monitor to the tile via 84/max(fw,fh) — correct for this square-ish art
        meta = {"frames": len(frames), "fw": cw, "fh": ch, "fps": fps,
                "anchorX": 0.5, "anchorY": 0.5}
        with open(os.path.join(out, f"terminal_{kind}.json"), "w") as fh:
            json.dump(meta, fh)
        print(f"wrote terminal_{kind}: {len(frames)} frames {cw}x{ch} @ {fps}fps")


if __name__ == "__main__":
    build()
