# Animation research: making generated people move well

The question: how to make procedurally generated characters move so that their motion is
**functional** (they walk, carry, sit, talk without looking broken), **aesthetic** (it has the
drawn, Ghibli quality) and **expressive** (it shows who they are and how they feel), for bodies
that are all different and with no motion-capture or keyframe library.

| file | contents |
|---|---|
| [principles.md](principles.md) | the historical and craft tradition: Muybridge and Marey, Disney's twelve principles (Thomas & Johnston), Lasseter 1987, Williams and Blair on walks, Japanese practice (drawing on ones, twos and threes; tame and tsume; ma), what Ghibli's timing actually is (measured) |
| [expressive_motion.md](expressive_motion.md) | how motion carries personality and emotion: Laban Movement Analysis, EMOTE, **PERFORM (Big Five → Laban Effort → motion parameters, with the published numbers)**, emotion in gait (Roether, Troje, Unuma), tension and relaxation (Neff & Fiume), Perlin's Improv, idle motion, gaze, gesture (Kendon, McNeill, BEAT), perception |
| [procedural_methods.md](procedural_methods.md) | the contemporary toolbox: procedural keys (Overgrowth), noise, springs, the cartoon animation filter, IK (analytic two-bone, FABRIK), foot planting (Johansen's footbase), sub-joint exaggeration, motion matching, neural and phase-based controllers, physics-based control; what fits us |
| [gait_reference.md](gait_reference.md) | numbers for the walk: normative joint angles, pelvic motion, step width, cadence; Muybridge observations |
| [motion_design.md](motion_design.md) | **the design of our procedural animation generator**: the rig (bones to add), the layers (intent → poses and cycles → style from personality/emotion/body → timing → secondary motion → constraints), and the tools |

Local material (gitignored): `reference/papers/animation/` (13 papers), `reference/animation/muybridge/`
(86 plates from *Animal Locomotion*, 1887, public domain, via Wikimedia Commons), and
`reference/ghibli/sakuga/` (326 key-animation clips: 72 walk cycles, 155 acting, 129 running, 84
fabric).  Measured data (committed): `data/drawing_rate.json`.

## Conclusions
1. **Procedural animation should work in poses, not formulas.** The best procedural systems
   (Overgrowth, Spore, EMOTE) interpolate a small set of strong key poses and let physics-like
   rules (springs, noise, IK) do the in-between. Our first animator computed joint angles from sine
   waves, and that's why it read as rigid. Good animation is pose, timing and spacing.
2. **Personality maps to motion quantitatively.** PERFORM's perceptual studies give a matrix
   from the Big Five to Laban's four Efforts (Space, Weight, Time, Flow) and a regression from Efforts
   to ~35 low-level motion parameters. Our people already have Big Five traits. Emotion in gait
   has measured signatures too (Roether 2009): a lowered head for sadness, bent elbows for
   anger and fear, bigger movement for happy and angry, smaller for sad and fearful.
3. **Ghibli timing is mostly on threes, with holds.** Measured over 226 Ghibli key-animation
   clips: walks spend 42% of screen time on threes, 24% on twos, 21% on ones, and 12% in holds of 6+
   frames; acting is similar (35 / 32 / 19 / 12). The choice follows speed: ones for fast action,
   threes for ordinary movement, holds for thought (ma).
4. **Anticipation needs the future, and we have it.** The cartoon animation filter (Wang et al.
   2006) makes anticipation and follow-through from any motion curve, but anticipation looks
   ahead. Our NPCs act from plans (walk here, stop, turn, pick up), so the generator knows what
   comes next and can anticipate it, which reactive game animation can't.
5. **Feet must not slide.** Perception studies (Hodgins et al. 1998) show that viewers notice motion
   errors more on more detailed bodies. Foot planting (Johansen's footbase IK) and correct
   ground contact matter more than any stylistic flourish.
6. **Bones to add:** a toe (ball of the foot) for heel-toe roll; a split spine (lumbar, thoracic)
   for curves and breathing; a second neck bone; forearm twist; secondary chains for hair clumps,
   ponytails and braids, skirt and coat hems, apron and bag straps. Eyes, lids, brows and mouth
   stay in the face shader, driven by animated parameters.
