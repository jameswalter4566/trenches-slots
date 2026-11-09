BLUE DIAMOND — IDLE + GLOW

54 transparent RGBA PNG frames: 27 idle + 27 glow, 512 x 512 each.
24 fps, 1.125 seconds per clip.

Each clip includes a 4608 x 1536 atlas (9 columns x 3 rows), three
1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON, motion JSON
and RGBA APNG. Read left to right, top to bottom. Preserve the full
512 x 512 cells with a centered pivot. Do not trim the frames.

Idle loops with a restrained cyan glow and subtle facet sheen.
Glow is a one-shot win: light builds over frames 01-13, peaks
over 14-17, and softens over 18-24. Frames 25-27 fade the whole
symbol. Final frame 27 is entirely transparent RGBA zero.

The diamond illustration is fixed throughout: no translation,
rotation, scaling, warping or independently redrawn frames. Only
lighting changes. Glow follows the gemstone contour with real
partial alpha and transparent pixels beyond it; no background fill.
Use ordinary source-over alpha blending in the game engine.

Glow frame 01 exactly matches idle frame 01. Transition after
the idle wraps, or blend to the entry lighting in your engine.

preview/diamond_idle_then_glow.gif shows both clips at slower
review speed on dark and purple tiles. These test backgrounds
are not in the production PNGs or APNGs. No audio is included.

Rebuild: python source/build_assets.py
Requires Python, Pillow, NumPy and SciPy. Source master, prompt,
renderer, neutral still and animation records included.
validation.json records alpha, canvas sizes, frame count, exact
atlas/APNG matching, seamless idle wrap and the blank last frame.
