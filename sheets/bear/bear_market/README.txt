BEAR MARKET — IDLE + ROAR

54 transparent RGBA frames total: 27 idle + 27 roar, 512 x 512 each.
24 fps, 1.125 seconds per animation.

Each animation includes a 4608 x 1536 atlas (9 columns x 3 rows), three
1536 x 1536 sheets (3 x 3), individual PNGs, JSON atlas and RGBA APNG.
Read left to right, then top to bottom. Keep the full 512 x 512 canvas.

Idle loops continuously. Roar plays once: anticipation, jaw opens,
chest and paws rise, red shockwaves and cash scatter, then recovery
and fade. Roar frame 27 is entirely transparent RGBA zero.
Roar frame 01 matches idle frame 01. Start roar after idle wraps,
or blend to its first frame in your game.

Original bear colors, eyes and body are unchanged. Only the mouth
region uses the matching generated roar keypose. All intermediate
frames use the same source art with deterministic local deformation.

preview/bear_idle_then_roar.gif shows both animations on dark and
purple test tiles at slower review speed. Test backgrounds are NOT
in the production PNGs or APNGs. No audio is included.

source/build_assets.py rebuilds exports using Python, Pillow, NumPy,
and SciPy. Generated master, keypose, isolated mouth, prompts and
motion records are included. validation.json records actual alpha,
frame count, canvas dimensions, blank finish, APNG and atlas checks.
