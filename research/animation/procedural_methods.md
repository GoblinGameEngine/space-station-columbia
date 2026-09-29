# Procedural and data-driven animation: the toolbox

What exists for moving characters without hand-keying every motion, and what fits a game with
hundreds of thousands of generated, all-different bodies and no motion library.

## Procedural (rules, no data): our path
- **Procedural key poses** (David Rosen, "An Indie Approach to Procedural Animation", GDC 2014,
  *Overgrowth*): the whole game's character animation came from about **13 keyframes**. Poses are
  interpolated by rules, with springs on the body and physics-like blending (crouch depth,
  lean into turns, landing squash) giving fluid, responsive motion. The lesson is that **a few
  strong poses plus good in-between rules beat formula-driven joints.**
- **Spore** (Hecker et al., SIGGRAPH 2008): animation authored once in a
  morphology-independent form and specialised per creature with IK.
- **Perlin noise and Improv** (1995/96): rhythmic and stochastic functions as joint drivers, and
  weighted action blending; personality from tuning.
- **Springs:** damped springs for secondary motion (hair, clothes, loose parts) and for the lag
  between body parts (overlap, drag). A critically damped or slightly underdamped spring is the
  standard game tool; its frequency and damping are a person's "tension".
- **The cartoon animation filter** (Wang, Drucker, Agrawala & Cohen, SIGGRAPH 2006) [local]:
  x\*(t) = x(t) − x̃″(t), subtracting a smoothed (Laplacian of Gaussian) second derivative from any
  motion curve. It produces **anticipation** (the negative lobe before a change),
  **follow-through** (after it) and exaggeration from one strength parameter, and it is fast
  enough for games. Applied with per-vertex time shifts, it also produces squash and stretch.
  Anticipation is non-causal, so it needs the motion's future. Our planned actions provide it.
- **Kochanek–Bartels splines** (tension, continuity, bias) for pose-to-pose paths: EMOTE's way of
  shaping arcs, sharpness and overshoot.
- **Sub-joint exaggeration** (Kwon & Lee, "Exaggerating Character Motions Using Sub-Joint
  Hierarchy", CGF 2008): limbs split into sub-links with Bézier interpolation and mass-springs,
  so they bend like rubber. This is the cartoon "rubber hose" look from extra bones; a later option
  for Ghibli's occasional stretch on fast action.

## Constraints
- **Analytic two-bone IK:** closed form for leg (hip–knee–ankle) and arm (shoulder–elbow–wrist);
  a pole vector picks the bend plane. Exact and cheap.
- **FABRIK** (Aristidou & Lasenby, Graphical Models 2011): forward-and-backward reaching IK on
  points, no matrices, fast convergence. Good for spines, tails and hair chains.
- **Foot planting** (Rune Skovbo Johansen, "Automated Semi-Procedural Animation for Character
  Locomotion", MSc 2009) [local]: analyse each cycle for foot lift and strike times; at run time
  blend by velocity and use leg IK so the feet land on the ground. The **footbase** is one heel+toe
  constraint that keeps the foot's alignment to the ground. This is how feet stop sliding and
  follow slopes.

## Data-driven (for reference; not our path)
- **Motion graphs** (Kovar, Gleicher & Pighin 2002): transitions between clips.
- **Verbs and adverbs** (Rose, Cohen & Bodenheimer 1998): interpolating example motions over
  style parameters.
- **Motion matching** (Simon Clavet, GDC 2016, *For Honor*): search a large motion-capture
  database every few frames for the frame best matching the current pose and the desired future
  trajectory. Near-mocap quality with no hand-built state machine, but it needs the data, and
  one body's data.
- **Neural controllers:** Phase-Functioned Neural Networks (Holden, Komura & Saito 2017);
  Neural State Machine (Starke et al. 2019); **DeepPhase** (Starke, Mason & Komura, SIGGRAPH 2022)
  [local], where a Periodic Autoencoder learns a phase manifold of each body part's periodicity;
  in-betweening with phase manifolds (Starke et al. 2023) [local].
- **Physics-based:** NaturalMotion's Euphoria (active ragdolls); DeepMimic (Peng et al. 2018)
  and AMP (2021), policies trained to imitate mocap in simulation.

These all need motion data, usually for one skeleton, and GPU or ML inference. Our bodies differ
per person and we have no mocap; the Deck's budget is small. What we take from them is the
**phase idea**: a gait is a set of periodic channels with their own phases and amplitudes. We
generate those channels procedurally instead of learning them.

## What fits us
**Pose-based procedural animation** (Overgrowth, EMOTE, Improv):
- key poses defined as data, in body-relative terms, so they fit any proportions;
- cycles built from those poses (contact, down, passing, up) with timing from the gait trait;
- style from personality and emotion via Laban Effort (PERFORM's numbers);
- springs for overlap and secondary motion;
- the cartoon filter for anticipation and follow-through on planned actions;
- two-bone IK with footbase planting for contact;
- a per-action drawing rate (threes, twos, ones) for the Ghibli timing.

All of it is cheap enough to run for dozens of characters on the Deck.
