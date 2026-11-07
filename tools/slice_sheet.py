#!/usr/bin/env python3
"""Slice a ChatGPT-generated sprite-sheet grid into a clean horizontal strip + JSON.

Usage:
  python tools/slice_sheet.py <sheet.png> <symbol> <kind> [rows] [cols] [fps]
  python tools/slice_sheet.py sheets/rocket_win.png rocket win 3 3 14

Reads an RxC grid image (transparent background), drops empty cells,
re-centers every frame on its alpha bounding-box center (kills the frame
jitter AI generators produce), and writes:

  public/symbols/anim/<symbol>_<kind>.png   one-row strip, uniform frames
  public/symbols/anim/<symbol>_<kind>.json  {"frames": N, "fw": W, "fh": H, "fps": F}

The game auto-loads both on refresh. Requires: pip install pillow
"""
import json
import os
import sys

from PIL import Image


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src, sym, kind = sys.argv[1:4]
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    cols = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    fps = int(sys.argv[6]) if len(sys.argv) > 6 else 14

    im = Image.open(src).convert("RGBA")
    w, h = im.size
    fw, fh = w // cols, h // rows

    cells = []
    for r in range(rows):
        for c in range(cols):
            frame = im.crop((c * fw, r * fh, (c + 1) * fw, (r + 1) * fh))
            bbox = frame.split()[3].getbbox()  # alpha-channel bounding box
            if bbox:
                cells.append((frame, bbox))
    if not cells:
        sys.exit("no non-empty frames found - is the background transparent?")

    pad = 10
    bw = max(b[2] - b[0] for _, b in cells)
    bh = max(b[3] - b[1] for _, b in cells)
    cw, ch = bw + pad * 2, bh + pad * 2

    strip = Image.new("RGBA", (cw * len(cells), ch), (0, 0, 0, 0))
    for i, (frame, b) in enumerate(cells):
        content = frame.crop(b)
        ox = i * cw + (cw - (b[2] - b[0])) // 2
        oy = (ch - (b[3] - b[1])) // 2
        strip.paste(content, (ox, oy), content)

    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "public", "symbols", "anim",
    )
    os.makedirs(out_dir, exist_ok=True)
    strip.save(os.path.join(out_dir, f"{sym}_{kind}.png"))
    with open(os.path.join(out_dir, f"{sym}_{kind}.json"), "w") as f:
        json.dump({"frames": len(cells), "fw": cw, "fh": ch, "fps": fps}, f)
    print(f"{sym}_{kind}: {len(cells)} frames {cw}x{ch} @ {fps}fps -> public/symbols/anim/")


if __name__ == "__main__":
    main()
