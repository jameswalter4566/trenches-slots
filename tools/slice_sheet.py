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


def _body_stats(frame: Image.Image):
    """(centroid_x, centroid_y, body_pixel_count) for the symbol's own saturated
    color — NOT the warm flame (R&G both high) and NOT gray/white smoke (low
    saturation). Pins the symbol in place and measures how much of it is present
    (used to trim fly-away tail frames). Returns (None, 0) if no body found."""
    px = frame.load()
    w, h = frame.size
    sx = sy = sw = 0.0
    count = 0
    step = 2 if w * h > 40000 else 1  # subsample big cells for speed
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b, a = px[x, y]
            if a < 150:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            sat = mx - mn
            if sat < 55 or mx < 110:
                continue  # gray smoke / dim
            if r > 150 and g > 110 and b < 120:
                continue  # orange/yellow flame
            sx += x * sat
            sy += y * sat
            sw += sat
            count += 1
    if sw == 0:
        return None, 0
    return (sx / sw, sy / sw), count


def _body_box(frame: Image.Image):
    """Bounding box of the symbol's saturated body (excludes flame/smoke)."""
    px = frame.load()
    w, h = frame.size
    minx = miny = 10 ** 9
    maxx = maxy = -1
    step = 2 if w * h > 40000 else 1
    for y in range(0, h, step):
        for x in range(0, w, step):
            r, g, b, a = px[x, y]
            if a < 150:
                continue
            mx, mn = max(r, g, b), min(r, g, b)
            if mx - mn < 55 or mx < 110:
                continue
            if r > 150 and g > 110 and b < 120:
                continue
            minx, miny = min(minx, x), min(miny, y)
            maxx, maxy = max(maxx, x), max(maxy, y)
    if maxx < 0:
        return None
    return (minx, miny, maxx, maxy)


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


def _clean(im: Image.Image) -> Image.Image:
    """Normalize an input image's alpha: key a baked background, or scrub AI haze
    and dark halo. A no-op on clean straight-RGBA frames."""
    hist = im.split()[3].histogram()
    transparent_px = sum(hist[:128])
    if transparent_px < im.width * im.height * 0.005:
        # no real transparency: baked background. Flood-fill key from the border
        # so only edge-connected background dies; art-internal whites survive.
        return key_background(im)
    # scrub AI alpha haze: anything below the floor becomes fully transparent
    a = im.split()[3].point(lambda v: 0 if v < 32 else v)
    im.putalpha(a)
    # dark-haze kill: dim + semi-transparent baked halo cleared, bright art kept
    _kill_dark_haze(im, lum_max=70, alpha_max=150)
    return im


def main() -> None:
    if len(sys.argv) < 4:
        print(__doc__)
        sys.exit(1)
    src, sym, kind = sys.argv[1:4]
    rows = int(sys.argv[4]) if len(sys.argv) > 4 else 3
    cols = int(sys.argv[5]) if len(sys.argv) > 5 else 3
    fps = int(sys.argv[6]) if len(sys.argv) > 6 else 14
    # 7th arg: "full" keeps every frame (play the complete launch-and-exit);
    # default "trim" drops the fly-away tail so the symbol stays in its tile.
    do_trim = (sys.argv[7].lower() != "full") if len(sys.argv) > 7 else True

    cells = []
    aligned = False  # folder of pre-aligned frames -> don't re-center per frame

    if os.path.isdir(src):
        # folder of individual frame PNGs (already a full, shared-coordinate
        # canvas each). Sort by name, clean each, keep as-is. No grid cutting.
        import glob
        paths = sorted(glob.glob(os.path.join(src, "*.png")))
        if not paths:
            sys.exit(f"no PNG frames found in folder {src}")
        aligned = True
        fw = fh = 0
        for p in paths:
            frame = _clean(Image.open(p).convert("RGBA"))
            fw, fh = frame.size
            bbox = frame.split()[3].getbbox()
            if bbox:
                cells.append((frame, bbox))
        print(f"loaded {len(cells)} pre-aligned frames from folder")
    else:
        im = _clean(Image.open(src).convert("RGBA"))
        w, h = im.size
        # rounded cell size + rounded origins: avoids sub-pixel drift accumulating
        # across many columns when the sheet isn't an exact multiple of the grid.
        fw, fh = round(w / cols), round(h / rows)
        for r in range(rows):
            for c in range(cols):
                x0, y0 = round(c * w / cols), round(r * h / rows)
                frame = im.crop((x0, y0, x0 + fw, y0 + fh))
                bbox = frame.split()[3].getbbox()  # alpha-channel bounding box
                if bbox:
                    cells.append((frame, bbox))
    if not cells:
        sys.exit("no non-empty frames found - is the background transparent?")

    stats = [_body_stats(f) for f, _ in cells]
    anchors = [s[0] for s in stats]
    counts = [s[1] for s in stats]

    # TRIM the fly-away tail: AI motion sheets often launch the subject off the
    # cell in the final frames. For a slot tile the symbol must stay put, so drop
    # trailing frames where the body has either (a) mostly left (< 45% of peak
    # body pixels) or (b) DRIFTED too far from its home position (> 16% of the
    # cell) — this catches a subject that is tilting/sliding out of frame while
    # still largely visible. Keeps the in-place lead-in intact.
    peak = max(counts) if counts else 0
    home = next((a for a in anchors if a), None)
    drift_max = 0.16 * min(fw, fh)
    if do_trim and peak and home:
        def gone(i: int) -> bool:
            if counts[i] < 0.45 * peak:
                return True
            a = anchors[i]
            if a is None:
                return True
            return ((a[0] - home[0]) ** 2 + (a[1] - home[1]) ** 2) ** 0.5 > drift_max
        last = len(cells) - 1
        while last > 0 and gone(last):
            last -= 1
        keep = last + 1
        if keep < len(cells):
            print(f"trimmed {len(cells) - keep} fly-away tail frame(s) (body left the cell)")
            cells = cells[:keep]
            anchors = anchors[:keep]

    # PIN the symbol body so it stays in place while its effect (flame, smoke,
    # splash, sparks) trails freely. Anchor = per-frame centroid of the body's
    # saturated color; align every frame's anchor to frame 0's. SKIPPED for
    # folder input: those frames are authored in a shared coordinate system and
    # must not be re-centered (their lead-in is already fixed-center).
    if aligned:
        shifted = [frame for frame, _ in cells]
    else:
        ref = next((a for a in anchors if a), None)
        if ref is None:
            anchors = [((f.width / 2), (f.height / 2)) for f, _ in cells]
            ref = anchors[0]
        shifted = []
        for (frame, _b), anch in zip(cells, anchors):
            a = anch or ref
            dx, dy = round(ref[0] - a[0]), round(ref[1] - a[1])
            canvas = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            canvas.paste(frame, (dx, dy), frame)
            shifted.append(canvas)

    # shared window = union of the aligned frames' bboxes
    boxes = [s.split()[3].getbbox() or (0, 0, s.width, s.height) for s in shifted]
    pad = 6
    ux0 = min(b[0] for b in boxes)
    uy0 = min(b[1] for b in boxes)
    ux1 = max(b[2] for b in boxes)
    uy1 = max(b[3] for b in boxes)
    cw, ch = (ux1 - ux0) + pad * 2, (uy1 - uy0) + pad * 2

    strip = Image.new("RGBA", (cw * len(shifted), ch), (0, 0, 0, 0))
    cell0 = None
    for i, s in enumerate(shifted):
        region = s.crop((ux0, uy0, ux1, uy1))
        if i == 0:
            cell0 = region
        strip.paste(region, (i * cw + pad, pad), region)

    # Where the symbol RESTS in frame 0 and how big it is — so the game can pin
    # the symbol body at the tile center and scale it to tile size, letting the
    # launch/jump overflow the cell instead of shrinking the whole (tall) frame.
    anchor_x, anchor_y, body_frac = 0.5, 0.5, None
    if cell0 is not None:
        bb = _body_box(cell0)
        if bb:
            cx = (bb[0] + bb[2]) / 2 + pad
            cy = (bb[1] + bb[3]) / 2 + pad
            anchor_x, anchor_y = round(cx / cw, 4), round(cy / ch, 4)
            body_frac = round((bb[2] - bb[0]) / cw, 4)

    out_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "public", "symbols", "anim",
    )
    os.makedirs(out_dir, exist_ok=True)
    strip.save(os.path.join(out_dir, f"{sym}_{kind}.png"))
    meta = {"frames": len(shifted), "fw": cw, "fh": ch, "fps": fps,
            "anchorX": anchor_x, "anchorY": anchor_y}
    if body_frac:
        meta["bodyFrac"] = body_frac
    with open(os.path.join(out_dir, f"{sym}_{kind}.json"), "w") as f:
        json.dump(meta, f)
    print(f"{sym}_{kind}: {len(shifted)} frames {cw}x{ch} @ {fps}fps "
          f"anchor({anchor_x},{anchor_y}) body={body_frac} -> public/symbols/anim/")


if __name__ == "__main__":
    main()
