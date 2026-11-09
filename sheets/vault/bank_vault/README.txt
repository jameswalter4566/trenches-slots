BANK VAULT — IDLE + UNLOCK

54 transparent RGBA PNG frames: 27 idle + 27 unlock, 512 x 512 each.
24 fps, 1.125 seconds per clip.

Each clip includes a 4608 x 1536 atlas (9 columns x 3 rows), three
1536 x 1536 sheets (3 x 3), individual PNGs, atlas JSON, motion JSON
and RGBA APNG. Read left to right, top to bottom. Keep full cells
and use a centered pivot; do not trim frames.

Idle: closed vault with a restrained reflection. Loops continuously.
Unlock: frames 01-09 turn the wheel through 180 degrees and slow
to a stop; 10-18 open the door on its fixed left hinge; 19-24 hold
the open cash reveal; 25-27 fade. Final frame is RGBA zero.
The bolts retract inside the frame before the door swings; bolt
sockets are visible on the thick door edge. Money stays inside.

The fixed shell comes from the approved concept. Generated clean
door and cash layers are composited into it. The same door and
wheel parts are transformed in every frame: no independent redraws.
Door movement uses a perspective hinge projection, not a crossfade.

Unlock frame 01 exactly matches idle frame 01. Switch at the idle
wrap or blend to the closed pose. Closed/open stills included.
preview/bank_vault_idle_then_unlock.gif is a slower review preview
on dark and purple tiles; those backgrounds are not in production
PNGs or APNGs. No audio is included.

Rebuild: python source/build_assets.py
Requires Python, Pillow, NumPy and SciPy. Original reference,
component artwork, masks, renderer and motion data included.
validation.json records actual alpha, dimensions, exact atlas/APNG
matching, loop entry matching and the fully blank last frame.
