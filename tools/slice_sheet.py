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


def _kill_dark_haze(im: Image.Image, lum_max: int, alpha_max: int) -> None:
    """Clear dim + semi-transparent pixels (baked dark halo); keep bright art."""
    px = im.load()
    w, h = im.size
    cleared = 0
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a == 0:
                continue
            lum = (r * 299 + g * 587 + b * 114) // 1000
            if lum <= lum_max and a <= alpha_max:
                px[x, y] = (r, g, b, 0)
                cleared += 1
    print(f"dark-haze kill: cleared {cleared} dim/semi px")


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
        # dark-haze kill: AI often bakes a dim mottled halo at mid alpha. Clear
        # pixels that are both DIM and SEMI-transparent (background), while bright
        # flame/smoke/art survives even at low alpha.
        _kill_dark_haze(im, lum_max=70, alpha_max=150)

    w, h = im.size
    # rounded cell size + rounded origins: avoids sub-pixel drift accumulating
    # across many columns when the sheet isn't an exact multiple of the grid.
    fw, fh = round(w / cols), round(h / rows)

    cells = []
    for r in range(rows):
        for c in range(cols):
            x0, y0 = round(c * w / cols), round(r * h / rows)
            frame = im.crop((x0, y0, x0 + fw, y0 + fh))
            bbox = frame.split()[3].getbbox()  # alpha-channel bounding box
            if bbox:
                cells.append((frame, bbox))
    if not cells:
        sys.exit("no non-empty frames found - is the background transparent?")

    # ONE shared window for every frame = the union of all frame bounding boxes
    # in cell-local coordinates. Each frame keeps its position within the cell,
    # so deliberate motion (a rocket rising, a flame/smoke trail growing) is
    # preserved and frames stay aligned. Per-frame re-centering is WRONG for
    # motion animations: as the trail changes shape the subject appears to slide.
    pad = 6
    ux0 = min(b[0] for _, b in cells)
    uy0 = min(b[1] for _, b in cells)
    ux1 = max(b[2] for _, b in cells)
    uy1 = max(b[3] for _, b in cells)
    cw, ch = (ux1 - ux0) + pad * 2, (uy1 - uy0) + pad * 2

    strip = Image.new("RGBA", (cw * len(cells), ch), (0, 0, 0, 0))
    for i, (frame, _b) in enumerate(cells):
        region = frame.crop((ux0, uy0, ux1, uy1))
        strip.paste(region, (i * cw + pad, pad), region)

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
