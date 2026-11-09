BULL — SEAMLESS IDLE ANIMATION

Original glossy chestnut bull with ivory horns, a gold nose ring, and dark hooves.
Motion: gentle breathing, small head movement, tail swish, and one front-hoof tap.
All 27 frames use one master illustration, with small continuous local deformations.
No independent image generation per frame.

DELIVERY
  frames/bull_idle_01.png through bull_idle_27.png: 512 x 512 RGBA PNG.
  bull_idle_atlas_9x3.png: 4608 x 1536; nine columns by three rows.
  bull_idle_atlas_9x3.json: untrimmed frame rectangles and animation order.
  sheets/: three 1536 x 1536 sheets, each a 3 x 3 grid of nine frames.
  bull_idle.apng: transparent animation using the exact same 27 frames.
  preview/bull_idle_dark_and_purple.gif: review-only colored backgrounds.
  source/: clean master, neutral 512 px icon, motion parameters, prompt, renderer.
  validation.json: alpha, dimensions, pixel equality, and loop verification.

PLAYBACK
  Recommended: 24 FPS, 1.125 seconds per loop. Repeat indefinitely.
  For a calmer idle, play at 18 FPS, giving a 1.5-second loop.
  Read frames left to right, top to bottom. No gutters or atlas padding.
  Keep the full 512 x 512 canvas aligned at center anchor (0.5, 0.5).
  Do not trim/recenter based on each frame's visible bounding box.
  This is an idle loop: the bull stays visible in every frame, including frame 27.
  The underlying pose at frame 28 equals frame 01 exactly; there is no blank pause.
  PNGs contain straight RGBA alpha. Use normal alpha blending and standard
  engine texture premultiplication. No backgrounds, labels, or borders are baked in.

REBUILD
  Python 3 with Pillow, NumPy, SciPy: run source/build_assets.py.
  The renderer uses premultiplied alpha during deformation to keep edges clean.
  The original asset has no company logo or existing token branding.
