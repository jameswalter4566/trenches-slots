# GOD CANDLE — symbol art prompt pack (ChatGPT / gpt-image-1)

## How to use
1. Open ChatGPT (GPT-4o or later with image generation).
2. Paste the MASTER STYLE block + one symbol prompt per generation.
3. **After the first good result (do the rocket first), attach that image to every
   following prompt** and add: "Match the exact art style, lighting, outline weight
   and color treatment of the attached image." That locks the set together.
4. Ask for PNG with transparent background, 1024×1024. If the background comes back
   solid, reply: "Regenerate with a fully transparent background (alpha PNG)."
5. Save each file with the EXACT filename into:
   `C:\Users\james\trenches-slots\public\symbols\`
   The game auto-loads them on refresh — no code changes needed.

## Rules
- NO text, letters, numbers or watermarks baked into any image (the orb's
  multiplier number is rendered live by the game engine).
- Symbol centered, filling ~80% of the square canvas.
- One symbol per image, nothing else, transparent background.

---

## MASTER STYLE (paste at the top of every prompt)

> Chunky 3D cartoon casino slot symbol, thick rounded shapes, candy-gloss
> highlights, bold saturated colors, soft single top-light, subtle dark bottom
> edge like thick vinyl toy plastic, clean silhouette, centered on a fully
> transparent background, 1024x1024 PNG, mobile-game quality, no text, no
> watermark, no background elements.

---

## 1. rocket.png (top symbol)
Cartoon rocket ship tilted 45 degrees climbing to the upper right, glossy white
body with green `#2be26a` fins and accents, round porthole window, big stylized
orange-yellow flame burst from the engine, tiny motion sparkles.

## 2. whale.png
Fat, round, glossy cartoon whale in deep blue with a pale belly, tiny contented
smile, small water spout puff above its blowhole, flippers tucked like it's
holding a bag.

## 3. frog.png
Original chunky cartoon frog, round body, huge glossy bulging eyes, wide smug
grin, bright green skin with a lighter belly, tiny gold chain necklace. An
original character design — must NOT resemble Pepe the Frog or any existing
meme or cartoon character.

## 4. diamond.png (diamond hands)
Brilliant-cut glossy blue diamond gripped tightly from both sides by two small
chunky golden cartoon hands, light refraction sparkles inside the gem.

## 5. moon.png
Glossy golden-cream full moon with soft round craters, a tiny green flag planted
on top, faint sparkle ring around it.

## 6. coinG.png (gold coin)
Thick cartoon casino coin seen straight on, glossy GOLD face, chunky beveled rim
with notches, embossed dollar-sign symbol in the center, candy shine highlight.

## 7. coinP.png (purple coin)
Same thick cartoon casino coin, glossy PURPLE face, chunky beveled rim with
notches, embossed upward trending chart arrow in the center, candy shine
highlight. Identical coin design language as the gold coin.

## 8. coinB.png (blue coin)
Same thick cartoon casino coin, glossy BLUE face, chunky beveled rim with
notches, embossed percent-sign symbol in the center, candy shine highlight.
Identical coin design language as the gold coin.

## 9. coinT.png (teal coin)
Same thick cartoon casino coin, glossy TEAL face, chunky beveled rim with
notches, embossed four-pointed sparkle star in the center, candy shine
highlight. Identical coin design language as the gold coin.

## 10. scatter.png (GOD CANDLE scatter)
A majestic glossy GREEN trading candlestick (rectangular candle body with a thin
wick line extending from the top and bottom), wearing a small golden crown,
standing on a round golden pedestal base, radiant golden-green glow aura rays
behind it. Make it feel like a divine artifact.

## 11. orb.png (multiplier orb)
Glowing golden energy orb like a divine sphere, swirling molten-gold surface,
with a small bright green trading candlestick glyph floating in its center,
electric green energy crackles arcing around the outside. NO number on it.

---

---
---

# PART 2 — WIN SPRITE SHEETS (the premium animations)

Each symbol gets a 9-frame WIN celebration generated as ONE image (a 3x3 grid).
One image = perfect style consistency between frames. The slicer tool fixes
frame alignment afterwards, so don't stress tiny drift.

## Workflow
1. Generate each sheet below in ChatGPT (paste MASTER SHEET STYLE + the prompt).
2. Save the raw image as `sheets\<symbol>_win.png` in the repo
   (e.g. `C:\Users\james\trenches-slots\sheets\rocket_win.png`).
3. Run the slicer (needs `pip install pillow` once):
   `python tools\slice_sheet.py sheets\rocket_win.png rocket win 3 3 14`
   It writes the cleaned strip + JSON into `public\symbols\anim\` and the game
   plays it automatically on that symbol's wins. (Or just tell Claude to slice.)
4. Keep the static PNG from PART 1 too — it's the symbol at rest on the board.

## MASTER SHEET STYLE (paste at the top of every sheet prompt)

> A 2D game animation sprite sheet: EXACTLY 9 frames arranged in a 3x3 grid,
> read left to right, top to bottom. Every cell is exactly one third of the
> image width and height. The subject appears at the IDENTICAL scale and
> centered position in every cell — only the animation pose changes between
> frames. Chunky 3D cartoon casino slot style, candy-gloss highlights, bold
> saturated colors, thick vinyl-toy shapes, fully transparent background,
> NO grid lines, NO borders, NO text, NO numbers, NO watermark.

## Sheet prompts

### rocket_win.png — ignition & liftoff
The glossy white cartoon rocket with green #2be26a fins: frames 1-3 engine
sparks then small flame ignites, frames 4-6 flame grows huge with smoke puffs
below, frames 7-9 rocket blasts upward inside its cell leaving vertical motion
streaks and sparks behind.

### whale_win.png — jump & splash
The fat glossy blue cartoon whale: frames 1-2 crouches/coils downward, frames
3-5 leaps upward in an arc with water droplets trailing, frames 6-7 peak of the
jump with a big smile, frames 8-9 splashes down with a burst of blue water
droplets around it.

### frog_win.png — spring jump
The chunky green cartoon frog with gold chain: frames 1-2 crouches low and
squashes, frames 3-5 springs upward with legs extended and cheeks puffed,
frames 6-7 mid-air spin, frames 8-9 lands with a bounce and a grin. An original
character — must NOT resemble Pepe the Frog.

### diamond_win.png — flash & shatter
The brilliant blue diamond held by golden hands: frames 1-2 glows brighter with
light refractions, frames 3-4 bright white flash and cracks of light appear,
frames 5-7 bursts into glowing blue crystal fragments flying outward, frames
8-9 fragments dissolve into sparkles.

### moon_win.png — golden spin
The glossy golden full moon with the green flag: rotates one full turn across
the 9 frames showing different crater faces, with golden sparkle particles
growing around it, ending with a bright golden glow ring.

### coinG_win.png — gold coin flip
The thick gold cartoon casino coin with embossed dollar sign: performs one full
3D flip across the 9 frames — face on, turning, edge-on (thin), turning,
face on, turning, edge-on, turning, face on with a burst of tiny gold sparkles
in the final frame.

### coinP_win.png — purple coin flip
Identical 3D flip sequence, the PURPLE coin with embossed upward chart arrow,
purple sparkles in the final frame.

### coinB_win.png — blue coin flip
Identical 3D flip sequence, the BLUE coin with embossed percent sign, blue
sparkles in the final frame.

### coinT_win.png — teal coin flip
Identical 3D flip sequence, the TEAL coin with embossed four-pointed star, teal
sparkles in the final frame.

### scatter_win.png — divine flare
The crowned green god-candle on its golden pedestal: frames 1-3 the aura rays
grow and the crown glints, frames 4-6 green energy flames rise around the
candle body and the glow intensifies, frames 7-9 a radiant golden-green burst
with light rays shooting outward.

### orb_win.png — energy surge
The golden energy orb with the green candlestick glyph: frames 1-3 the electric
green crackles multiply and whip around it, frames 4-6 the orb surges blinding
bright with molten gold swirls, frames 7-9 releases a ring-shaped golden
shockwave outward.

## Optional round 3 — IDLE sheets (looping, after the win set works)
Same MASTER SHEET STYLE, but gentle motion that LOOPS: "frame 9 must flow
seamlessly back into frame 1". Save as `sheets\<symbol>_idle.png`, slice with
kind `idle` and ~10fps:
`python tools\slice_sheet.py sheets\whale_idle.png whale idle 3 3 10`
Good candidates: whale (tail sway + blowhole puff), frog (breathing + blink),
orb (crackle loop), scatter (aura pulse). The engine uses procedural idle
motion for any symbol without an idle sheet.
