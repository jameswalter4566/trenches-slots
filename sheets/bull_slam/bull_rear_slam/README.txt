BROWN BULL — REAR UP AND SLAM

The original brown bull crouches, lifts its shoulders and BOTH front legs,
folds the front knees, holds briefly, then slams both front hooves down.
Gold sparks, a ground-level impact wave and dust sell the landing. It settles,
holds, and fades to a fully transparent final frame.

The original bull's brown palette and facial features are preserved. Original
body/head artwork is combined with a matching folded-foreleg key pose.
There is no dark transformation, red-eye effect, or coat recoloring. The head,
horns, amber eyes, muzzle and gold nose ring keep the original design. Separate
shoulder, knee and ankle transforms articulate the front legs; the upper body
rises while the rear hoof baseline stays planted. No whole-symbol charge or zoom.

DELIVERY
  frames/bull_slam_01.png through bull_slam_27.png: 512 x 512 RGBA PNG.
  bull_slam_atlas_9x3.png: 4608 x 1536, 9 columns by 3 rows, no gutters.
  bull_slam_atlas_9x3.json: untrimmed frames and animation order.
  sheets/: three 1536 x 1536, 3 x 3 sheets: 01–09, 10–18, 19–27.
  bull_slam.apng: transparent animated preview, 24 FPS, one play.
  preview/bull_rear_slam.gif: slower inspection on dark and purple backgrounds.
  source/: original aligned artwork, rig parts, bone data, renderer, motion data.
  validation.json: alpha, dimensions, export equality, and blank-ending checks.

PLAYBACK
  24 FPS = 1.125 seconds; 18 FPS = 1.5 seconds for a more deliberate action.
  Read cells left to right and top to bottom. Keep all 512 px canvases aligned.
  Use center anchor (0.5,0.5); do not trim or recenter individual visible bounds.
  Frame 01 matches the original Bull Idle frame 01 exactly.
  Play once, including frame 27, which has all RGBA values equal to zero.
  Background colors appear only in the review GIF, never in the production PNGs.
  Use ordinary alpha blending; PNGs contain straight RGBA alpha.

REBUILD
  Python 3 with Pillow, NumPy, SciPy: run source/build_assets.py.
