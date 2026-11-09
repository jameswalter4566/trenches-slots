MONEY GUN — IDLE + CASH BURST

54 transparent RGBA PNG frames: 27 idle + 27 fire, 512 x 512 each.
24 fps, 1.125 seconds per clip.

Each clip includes a 4608 x 1536 atlas (9 columns x 3 rows), three
1536 x 1536 sheets (3 x 3), individual PNGs, JSON atlas and RGBA APNG.
Read left to right, then top to bottom. Use full 512 x 512 cells
with centered pivot; disable trimming.

Idle loops with a gentle float and tilt. Fire plays once: wind-up,
recoil and a continuous burst of 14 fluttering notes, followed by
settling and fade. Fire frame 27 is fully transparent RGBA zero.
Fire frame 01 matches idle frame 01. Switch after the idle wraps or
blend to the first fire frame in the engine.

The same gun artwork is used in every frame. Banknotes reuse one
matching isolated bill. Notes emerge from a masked front opening.
No logos, numbers or portraits appear on the artwork. No audio.

preview/money_gun_idle_then_fire.gif shows both clips at slower
review speed on dark and purple test backgrounds. Those backgrounds
are not in the production PNGs or APNGs.

Rebuild with Python, Pillow, NumPy and SciPy: python source/build_assets.py
Source masters, renderer, generation prompts and motion data included.
validation.json records alpha, dimensions, exact atlas/APNG matching,
seamless idle wrap and the blank final firing frame.
