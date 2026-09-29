# Design: the procedural animation generator

This builds on the research in this folder. It replaces the first animator (sine-driven joints plus
springs) with a pose-based, style-driven, constraint-correct generator. It is written as
`remake/characters/npc_motion*.gd` with its data in `npc_motion.json`.

## 1. Rig
Current: 39 bones (body 19, fingers 20). To add:
- **Toes** (ToeL, ToeR at the ball of the foot): heel-to-toe roll and push-off (ankle −20° with the
  toe bending) is half of a walk's weight.
- **Spine:** Hips → Spine → Chest is enough for a curve. Breathing moves the Chest.
- **Secondary chains** (driven by springs, not by the pose):
  - hair: 2 bones for a ponytail or braid, 2 for a long curtain;
  - skirts and coat hems: 4 bones round the hem (front, back, left, right), each hanging from the hips;
  - a bag or apron strap: 1 bone.
- **Face** (shader parameters, animated): pupil offset (gaze), blink, brow raise, mouth open
  and shape (speech, smile). No bones.

## 2. Layers (evaluated every sampled frame)
1. **Intent.** What the person is doing now and next, from their plan (NpcPopulation): stand,
   walk to X, turn, stop, look at Y, talk (with gestures), pick up, sit. Because the plan is
   known, the next event is known, and that is what anticipation needs.
2. **Poses and cycles.**
   - *Walk:* four key poses per step (contact, down, passing, up) as data, in joint angles relative
     to rest, from `gait_reference.md`, interpolated through the cycle with Kochanek–Bartels
     splines (tension and bias from Effort).
   - *Idle:* a library of stances (neutral; weight on one leg; hands behind the back; arms
     folded; hands clasped in front; hand on hip), chosen by personality, with balance shifts
     (Egges) and long holds (ma).
   - *Gestures:* Kendon phases (prep → stroke → hold → retract) over McNeill types; beats timed to
     speech; deictic gestures toward the thing talked about.
3. **Style.**
   - *Personality → Laban Effort* by the PERFORM matrix (`expressive_motion.md` §3), then Effort →
     speed, anticipation, overshoot, torso rotation, head-look frequency and magnitude, breathing,
     arm spread or enclosure, and sink or rise.
   - *Mood → Roether features:* head inclination (sad), elbow flexion (angry, afraid), movement
     amplitude (up for happy and angry, down for sad and afraid).
   - *Body → gait:* elders shorten the step, widen the base, lean forward and swing the arms less;
     children quicken the cadence and bounce; heavy bodies widen and sway.
   - *Tension:* spring stiffness and damping per person (Neff & Fiume): a relaxed person has loose
     arms that swing and settle, a tense one moves stiffly.
4. **Timing.**
   - Transitions ease with the Effort time exponent, with tame (a hold or slow build) before a
     tsume snap.
   - Anticipation and follow-through come from the cartoon filter applied to planned transitions
     (starts, stops, turns, gesture strokes).
   - The pose is sampled at a drawing rate per action: threes for ordinary walking and acting, twos
     for brisk movement, ones for fast action (measured Ghibli practice, `principles.md` §4). This
     can be switched off, and will be tested against the moving first-person camera.
5. **Secondary.** Springs on the arms (drag), head (lag and settle), hair chains and hems (hanging
   from hips and head, driven by their acceleration and the wind), breathing, blinks and saccades
   (eyes lead, head follows).
6. **Constraints.**
   - The feet are planted: each stance foot keeps its ground position until lift-off (two-bone
     leg IK, a footbase per foot on the ground under it, following slopes).
   - Step width is narrow: feet near the midline.
   - Look-at is split between eyes, head and chest.
   - The hands reach held objects.

## 3. Data
`npc_motion.json` holds the key poses (walk keys, idle stances, gesture shapes), the Effort
mappings (the PERFORM tables), the mood features, the age and body modifiers, and the drawing
rates. It is extensible like the trait files: add a stance or a gesture by adding an entry.

## 4. Tools
- `npc_lineup.gd walk` (exists): one person at N phases.
- **onion skin:** N frames of a motion overlaid in one image, to judge arcs and spacing (the
  animator's light table).
- **curves:** a joint angle over the gait cycle plotted against the normative band from
  `gait_reference.md`.
- **personalities:** one body walking with five personality extremes side by side, to check that
  the Effort mapping reads.
- **the in-game check:** DevBridge to watch residents walk and idle, frame times.

## 5. Order of work
1. Toes; key-pose walk with normative angles; foot planting; narrow base; pelvis
   list/rotation/shift; arms across the body; age and body modifiers.
2. Personality → Effort → parameters (PERFORM); mood features (Roether).
3. Idle stances, balance shifts, holds; gaze with eyes leading the head, blinks (face shader
   parameters).
4. Timing: the drawing rate; cartoon filter anticipation on starts, stops and turns.
5. Secondary chains: hair, hems.
6. Gestures for conversation (with the dialogue system).

## 6. Status (2026-09-29)
Built (`remake/characters/npc_animator.gd`, `npc_style.gd`; tests in `remake/tools/`):
- **Rig:** 43 bones, including toes, hands with fingers and the hair chain (HairA, HairB).
- **Walk:** foot-trajectory IK walk with planted feet, heel-toe roll, a narrow base, and pelvis
  bob, shift, list and rotation.
- **Style:** personality → Effort → motion parameters (PERFORM); mood features (Roether); age and
  body.
- **Idle:** stances by arm IK chosen by personality; balance shifts; glances with eyes leading;
  blinks.
- **Starts, stops and turns:** anticipation on starts, lean follow-through on stops, head-led
  turns, smooth body turns.
- **Talking:** beat gestures (Kendon phases), nods and a speaking mouth.
- **Secondary:** hair swing; skirts carried per vertex by the legs.
- **Drawing rate:** a switch (`NpcPopulation.set_drawing_rate(3)` for threes), to be judged in
  game.

Next:
- hem bones for coats and skirts (springs);
- iconic and deictic gestures tied to what is said;
- sitting, carrying, work idles by occupation (the Ghibli "spectacular mundane");
- per-foot ground height on slopes;
- the cartoon filter on gesture strokes.
