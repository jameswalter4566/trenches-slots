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


def key_background(im: Image.Image, tol: int = 26) -> Image.Image:
    """Remove the baked background: BFS from every border pixel, clearing pixels
    whose color is within `tol` per channel of the median corner color."""
    from collections import deque

    w, h = im.size
    px = im.load()
    corners = [px[1, 1], px[w - 2, 1], px[1, h - 2], px[w - 2, h - 2]]
    bg = tuple(sorted(c[i] for c in corners)[2] for i in range(3))

    def is_bg(p):
        return abs(p[0] - bg[0]) <= tol and abs(p[1] - bg[1]) <= tol and abs(p[2] - bg[2]) <= tol

    seen = bytearray(w * h)
    q = deque()
    for x in range(w):
        for y in (0, h - 1):
            if not seen[y * w + x] and is_bg(px[x, y]):
                seen[y * w + x] = 1
                q.append((x, y))
    for y in range(h):
        for x in (0, w - 1):
            if not seen[y * w + x] and is_bg(px[x, y]):
                seen[y * w + x] = 1
                q.append((x, y))
    while q:
        x, y = q.popleft()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and not seen[ny * w + nx] and is_bg(px[nx, ny]):
                seen[ny * w + nx] = 1
                q.append((nx, ny))

    cleared = 0
    for y in range(h):
        row = y * w
        for x in range(w):
            if seen[row + x]:
                p = px[x, y]
                px[x, y] = (p[0], p[1], p[2], 0)
                cleared += 1
            else:
                p = px[x, y]
                if p[3] < 255:
                    px[x, y] = (p[0], p[1], p[2], 255)

    # soften the cut edge: halve alpha on art pixels touching the removed region
    for y in range(h):
        row = y * w
        for x in range(w):
            if not seen[row + x]:
                for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                    if 0 <= nx < w and 0 <= ny < h and seen[ny * w + nx]:
                        p = px[x, y]
                        px[x, y] = (p[0], p[1], p[2], 128)
                        break
    print(f"keyed baked background rgb{bg}: cleared {cleared} px")
    return im


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src, sym, kind = sys.argv[1:4]
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    cols = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    fps = int(sys.argv[6]) if len(sys.argv) > 6 else 14

    im = Image.open(src).convert("RGBA")

    hist = im.split()[3].histogram()
    transparent_px = sum(hist[:128])
    if transparent_px < im.width * im.height * 0.005:
        # no real transparency: baked background. Key it out by flood-filling
        # from the sheet border — only background CONNECTED to the edges is
        # removed, so white highlights inside the art survive.
        im = key_background(im)
    else:
        # scrub AI alpha haze: anything below the floor becomes fully transparent
        ALPHA_FLOOR = 32
        a = im.split()[3].point(lambda v: 0 if v < ALPHA_FLOOR else v)
        im.putalpha(a)

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
