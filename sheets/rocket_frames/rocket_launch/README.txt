ROCKET LAUNCH — 27 FRAMES

Production assets
  rocket_atlas_9x3.png       4608 x 1536, 9 columns x 3 rows, RGBA PNG
  rocket_atlas_9x3.json      Untrimmed atlas rectangles and animation order
  frames/rocket_01.png      Through rocket_27.png; each 512 x 512, RGBA PNG
  sheets/                  Three 1536 x 1536 sheets, each 3 x 3 / nine frames

Read frames left to right, then top to bottom. Each cell is exactly 512 x 512.
No padding, trimming, rotation, text, borders, or background in production PNGs.
All frame canvases use the same coordinates. Place the canvas at your slot's
center using anchor (0.5, 0.5). Do not recenter each frame on its visible bounds.

Playback
  Suggested rate: 24 frames/second (1.125 seconds for the complete sequence).
  Play once for a win animation. Clear the sprite after frame 27, then restore
  your idle symbol when needed. This is a launch-and-exit, not a seamless loop.
  PNG files contain straight RGBA alpha; use ordinary alpha compositing and
  let your rendering engine handle its normal texture premultiplication.

  Phase 1: frames 01–09: fixed center, smooth 236-to-274 px rocket height,
           subtle engine glow.
  Phase 2: frames 10–18: ignition, growing flame, smoke, 14 px initial lift.
  Phase 3: frames 19–27: upward acceleration and exit. The rocket is completely
           above the canvas by frame 25. Frames 25–27 retain fading effects.

Canvas 2D example (zero-based frameIndex)

  const atlas = new Image();
  atlas.src = './rocket_atlas_9x3.png';
  await atlas.decode();
  const fps = 24;
  const start = performance.now();
  function tick(now) {
    const frameIndex = Math.floor((now - start) * fps / 1000);
    ctx.clearRect(0, 0, 512, 512);
    if (frameIndex >= 27) return;
    const sx = (frameIndex % 9) * 512;
    const sy = Math.floor(frameIndex / 9) * 512;
    ctx.drawImage(atlas, sx, sy, 512, 512, 0, 0, 512, 512);
    requestAnimationFrame(tick);
  }
  requestAnimationFrame(tick);

Preview files
  preview/rocket_launch.apng and .webp preserve transparency and contain the
  exact same 27 frames at 24 fps. They loop for inspection only.
  preview/rocket_on_dark_and_purple.gif shows two review backgrounds. Those
  backgrounds exist ONLY in this preview GIF. GIF timing is approximately 25 fps.

Source and validation
  source/rocket_master.png is the single clean master used in every frame.
  source/build_animation.py deterministically renders the animation using
  Pillow, NumPy, and SciPy. Run it with Python 3 to rebuild the outputs.
  source/motion.json records every transform. No rocket is redrawn per frame.
  source/generation_prompt.txt records the original art prompt and method.
  validation.json records dimensions, alpha-channel checks, atlas equality,
  animation-frame equality, and the source hash.

The production assets were reviewed over dark and purple backgrounds.
The final delivery has also been checked numerically for genuine transparency.
