TRADING TERMINAL — IDLE + MODEST WIN

54 transparent RGBA PNG frames: 27 idle + 27 win, 512 x 512 each.
24 fps, 1.125 seconds per animation.

Each animation includes a 4608 x 1536 atlas (9 columns x 3 rows),
three 1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON,
motion JSON and RGBA APNG. Read left to right, top to bottom.
Keep full cells and use a centered pivot. Do not trim frames.

Idle: small scrolling price ticks and subtle data-bar updates.
The monitor casing and stand remain exactly still.
Win: the right end of the chart rises moderately, the display
briefly brightens, then settles at its higher level. Frames 25-27
fade the complete symbol. Frame 27 is entirely transparent RGBA zero.
All chart data is fictional decorative animation, not market data.

The approved monitor artwork is reused in every frame. A generated
blank display is composited into the original casing; all graph
animation is deterministic and clipped inside the screen. No
independent redraws, movement or color changes to the monitor case.

Win frame 01 exactly matches idle frame 01. Switch after the idle
wrap or blend to its entry frame in the engine.
preview/trading_terminal_idle_then_win.gif shows both clips at
slower review speed on dark and purple tiles. Test backgrounds
are not in production PNGs or APNGs. No audio is included.

Rebuild: python source/build_assets.py
Requires Python, Pillow, NumPy and SciPy. Source artwork, renderer,
masks, screen-plate prompt and motion data included.
validation.json records alpha, dimensions, exact atlas/APNG matching,
stationary case pixels and silhouette, loop entry, and blank finish.
