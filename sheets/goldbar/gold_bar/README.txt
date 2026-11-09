PLAIN GOLD BAR — IDLE + DROP AND SHINE

54 transparent RGBA PNG frames: 27 idle + 27 impact, 512 x 512 each.
24 fps, 1.125 seconds per animation. No numbers, stamps or logos.

Each animation includes a 4608 x 1536 atlas (9 columns x 3 rows),
three 1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON,
motion JSON and an RGBA APNG. Read left to right, top to bottom.
Use full 512 x 512 cells with centered pivot. Do not trim cells.

Idle: a stationary rigid bar with a subtle moving reflection. Loops.
Impact: frames 01-06 lift, 07-12 accelerate down to contact,
13-18 make one small bounce and settle, 19-24 sweep the highlight,
25-27 fade. Impact frame 27 is entirely transparent RGBA zero.
No squash, stretching, redesign or independent frame generation.
Impact frame 01 exactly matches idle frame 01; transition at the
idle wrap or blend to the entry pose in your game engine.

preview/gold_bar_idle_then_impact.gif shows both clips at slower
review speed on dark and purple tiles. Test backgrounds are not
in production PNGs or APNGs. No audio is included.

The source image is the approved plain-bar illustration. Source
master, rigid renderer, masks and motion data are included.
Rebuild: python source/build_assets.py
Requires Python, Pillow, NumPy and SciPy.
validation.json records alpha, dimensions, frame count, exact
atlas/APNG matching, seamless idle wrap and the blank finish.
