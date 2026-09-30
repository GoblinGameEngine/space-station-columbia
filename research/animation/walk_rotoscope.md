# The walk, rotoscoped: how the head and shoulders really move

The procedural walk (npc_animator.gd) looked rigid and wooden. Its legs followed good gait data
(gait_reference.md), but above the pelvis it was a stiff block: the head rode dead level, the
shoulders never tipped or swung, and the arms swung from a torso that ignored them. For this study
I rotoscoped real walkers frame by frame, measured the head and shoulders, and fitted the walk to
the measurements.

## Sources
Footage is in `reference/animation/walk/` (gitignored), with contact sheets in `study/` and
measurements in `roto/`.

| video | what it is | used for |
|---|---|---|
| "Male Walk Cycle Animation Reference – Front & Side Views in Slow Motion with Grid" (YouTube vq9A5FD8G5w) | one walk filmed from the side and the front at once, frame-numbered, on a grid; dark bodysuit | measured |
| "Larger Male Walk Cycle Animation Reference", same format (L3_em686qEE) | a heavy build | measured |
| "Female Walk Cycle Animation Reference", same format (G8Veye-N0A4) | light top: the silhouette tracker can't separate it | studied by eye |
| "Walk Reference – Casual – Male/Female, 60 fps" (F-Xy3_ln_BY, KLk22vSIdR4, sgRvk1m_WLs) | casual walks, slow motion | studied by eye |
| "Walk Happy Reference" (giv6UdPSzT8), "Angry Walk" (RmvMIKcTvqI, 2kFwBPojOSM) | mood walks | mood carriage |
| "Normal Gait: Side View" (mrheoxekvc8) | clinical gait | cross-check |
| Muybridge, *Animal Locomotion* (1887), plates in `reference/animation/muybridge/` | classic walking sequences | cross-check |

## Method (tools/charref/roto_walk.py)
1. **Frames.** Take every frame, skipping the slow-motion duplicates. The performer is segmented
   by silhouette against the white grid. The shoulder line is measured from the dark bodysuit
   alone, so the bare arms and neck drop out and the straps over the shoulders give a clean line.
2. **Measurements.**
   - Front view: the head's and the chest's sideways position, the shoulder-line tilt, and the
     apparent shoulder width, which narrows as the chest twists.
   - Side view: head height (the bob), the head ahead of the pelvis, and the stride.
3. **Phase.** Heel strikes are the stride maxima. Which foot leads comes from the front view: the
   leading foot is nearer the camera, so it sits lower in the image. Frames are folded onto one
   cycle (0 = right heel strike) and averaged in 20 bins, in fractions of body height H.
4. **Check sheets.** The measurements are drawn on the frames (`roto/*_check.jpg`), so a wrong
   landmark shows at a glance. The first pass put the "shoulders" on the neckline; the dark-suit
   pass fixed that.
5. **Comparison.** The game's walk is measured the same way by `remake/tools/npc_walk_measure.gd`
   (with springs running, several cycles), and `tools/charref/walk_compare.py` compares the two:
   peak-to-peak and shape correlation.

## What real walkers do (363 phase-labelled frames, two men)
- **Bob:** the head rises and falls 0.025–0.043 H a stride (4–7 cm), twice per cycle. It is lowest
  just after each heel strike and highest mid-stance. The heavier man bobs less.
- **Sideways:** the chest sways ±0.011 H over the standing leg. The **head swings further**
  (±0.02 H) and gets there first, peaking early in stance, like a pendulum carried on the trunk.
- **Shoulder tilt:** ±2.5–4° once per cycle. In the average man, the shoulder over the standing leg
  dips as it takes the weight: the counter-tilt to the hips that animators draw (Williams). The heavy
  man instead tips his shoulders *with* his hips, a waddle.
- **Twist:** the shoulders' apparent width narrows about 2% at each extreme, a chest rotation of
  about ±10–11° against the pelvis. The shoulders swing forward with the opposite leg.
- **Trunk pitch:** a small rock twice a stride. Measuring head-over-pelvis from the silhouette is
  contaminated by the thigh swinging through the pelvis band, so only the phase is trusted (the
  head behind just after contact, ahead before the next).
- **By eye** (the casual and mood walks):
  - the clavicles move with the arms (the shoulder leads each forward swing);
  - the eyes stay level, the head counter-tilting against the trunk;
  - in the angry walk the chest drives forward, the neck thrusts the head ahead, and the shoulders
    twist hard with bent, pumping arms.

## What was wrong in the game, and what changed
- **Every forward/back tilt was inverted.** The rig's +x rotation tips a bone back, but the walk
  treated it as forward. So:
  - "leaning into the walk" leaned people back, and so did elders' stoop;
  - sad people's "head down" tipped the head up;
  - the pelvis tilted the wrong way.
  
  Fixed throughout: the pelvis, spine, neck, head and hair. Much of the stiff, braced look was
  this.
- **The chest barely turned.** The counter-turn nearly cancelled the pelvis's yaw (±0.5° in the
  world). Now the chest turns about ±8° in the world against the pelvis, and the head stays
  stabilised, following it by about 15%.
- **New motion, fitted to the curves:**
  - the trunk leans over the standing leg (4.8°, phase 0.05);
  - the head swings sideways further than the chest while its roll stays level (4.5°, phase 0.1);
  - the trunk pitches twice a stride (2°, phase 0.35);
  - a small head nod as each heel strikes;
  - the clavicles move forward and back with the arm swing (6°);
  - the bob is raised to the measured 0.034 H.
- **By body:** `waddle` (heavy builds) blends the shoulders from counter-tilting to tipping with the
  hips, and trims the bob.
- **By mood:**
  - angry: chest forward 7°, neck jut 10°, 40% more twist;
  - sad: chest forward 5°, shoulders slumped forward and down, head down (now truly down);
  - happy: chest and head up;
  - afraid: shoulders hunched up 8°.

## Fit (game vs the two rotoscoped men)
| feature | reference peak-to-peak | game | shape r |
|---|---|---|---|
| head bob | 0.034 H | 0.033 H | +0.95 |
| head sideways (vs chest) | 0.0135 H | 0.0147 H | +0.94 |
| chest sideways | 0.021 H | 0.021 H | +0.69 |
| shoulder tilt | 5.1° | 5.9° | +0.88 |
| shoulder width (twist) | 0.0044 H | 0.0044 H | +0.53 |
| head over pelvis (fore-aft) | (contaminated) | 0.008 H | +0.65 |

Personality and mood scale all of this (`amp`, `sway`, `torso_turn`, `bounce`), so the fitted walk
is the neutral centre and no two people walk alike.
