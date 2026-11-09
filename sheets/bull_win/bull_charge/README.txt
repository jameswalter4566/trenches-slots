DARK BULL — LANDING / CHARGE ANIMATION

27 frames: original chestnut bull gradually changes to charcoal gunmetal with
red eyes, lowers its head, paws the ground, then accelerates toward the camera.
The bull grows closer, strides, and passes downward beyond the viewport. Dust
fades afterward. Frame 27 is completely blank, with every RGBA channel zero.

frames/bull_charge_01.png through bull_charge_27.png: 512 x 512 RGBA PNG.
bull_charge_atlas_9x3.png: 4608 x 1536, 9 columns by 3 rows, no gutters.
bull_charge_atlas_9x3.json: frame rectangles, ordering, and center pivot.
sheets/: three 1536 x 1536, 3 x 3 sheets, with frames 01–09, 10–18, 19–27.
bull_charge.apng: all 27 frames, transparent, plays once at 24 FPS.
preview/bull_charge_dark_and_purple.gif: slower review playback on two colors.
source/: aligned color states, entry frame, rendering script, and motion data.
validation.json: alpha, dimensions, sheet equality, full exit and blank-frame checks.

PLAYBACK
  Suggested game playback: 24 FPS, 1.125 seconds. Play once through frame 27.
  Use 18 FPS for a slower 1.5-second transformation and charge.
  Read frames left to right, then top to bottom.
  Center anchor: (0.5,0.5). Keep the full 512 px canvas fixed, without trimming.
  Frame 01 is pixel-identical to frame 01 of the existing Bull Idle pack.
  Switch at that neutral idle pose to avoid a small pose change on entry.
  All production PNG backgrounds are genuinely transparent. The two colored
  backgrounds appear ONLY in the review GIF. Its blank ending holds before repeat.

The original silhouette is retained during the color transition; the dark state
comes from an edited version of the same bull. Continuous deformation animates
the head, legs and tail. No 27 independent image-generation redraws are used.
The renderer uses premultiplied alpha internally; PNG outputs are straight RGBA.
Rebuild with Python 3, Pillow, NumPy and SciPy: source/build_assets.py.
