# The craft tradition: how animators make movement look good

## 1. Seeing motion: Muybridge and Marey
Eadweard Muybridge's *Animal Locomotion* (1887; 781 plates) photographed people and animals in
sequence against a grid, from several sides at once: walking, running, carrying, sitting down,
picking up, turning. Étienne-Jules Marey's chronophotography (1880s) put a movement on a single
plate. Animators have worked from these ever since. 86 plates are in
`reference/animation/muybridge/` (public domain).

**Observed on the walking plates** (e.g. "A woman walking", Wellcome V0048621, three views):
- the feet land close to a single line under the body, each step crossing slightly toward
  the midline, not at hip width;
- the pelvis drops on the swinging-leg side and shifts over the standing foot; the shoulders
  counter-tilt;
- at contact the front knee is straight and the heel strikes toe-up, while the back foot is up on
  its toes (push-off);
- the swing foot passes low, only just clearing the ground, with the knee bent most as it passes
  under the body;
- in an ordinary walk the arms swing little (≈15–20° at the shoulder), a little across the body,
  with the elbow slightly bent; hands relaxed;
- the head stays nearly level while the body bobs: the neck compensates.

## 2. Disney's twelve principles
Frank Thomas and Ollie Johnston, *The Illusion of Life: Disney Animation* (1981); brought to
3D by John Lasseter, "Principles of Traditional Animation Applied to 3D Computer Animation"
(SIGGRAPH 1987) [local].
1. **Squash and stretch:** volume kept while shape changes; gives weight and flexibility.
2. **Anticipation:** a preparatory move opposite to the action (the wind-up before a throw, the
   lean before a step); tells the viewer what is about to happen.
3. **Staging:** the pose reads clearly, silhouette first.
4. **Straight-ahead and pose-to-pose:** plan key poses, then in-betweens (pose-to-pose); or draw
   forward frame by frame. For us this means strong key poses plus rules for the in-between.
5. **Follow-through and overlapping action:** parts don't stop together; hair, clothes and
   loose flesh keep going and settle, and the body's parts move at different times (drag).
6. **Slow in and slow out:** more drawings near the keys, fewer between (easing).
7. **Arcs:** natural motion moves on arcs, not straight lines.
8. **Secondary action:** a supporting action that adds to the main one (a hand in a pocket while
   walking, a glance) without competing with it.
9. **Timing:** the number of frames for an action sets its weight, mood and personality.
10. **Exaggeration:** push the essence of a pose or action beyond the literal.
11. **Solid drawing:** volume, weight, balance; avoid "twins" (both limbs doing the same thing
    symmetrically).
12. **Appeal:** a design and movement the audience wants to watch.

Lasseter adds for 3D: a computer's even in-betweening and perfect symmetry kill life. Break
symmetry, vary timing between parts, and avoid moving everything at once.

## 3. The walk: Williams and Blair
Richard Williams, *The Animator's Survival Kit* (2001), and Preston Blair, *Cartoon Animation*
(1947, rev. 1994), are the standard references. The walk is **"a controlled fall"**: the body
falls forward and a leg catches it. Four key poses per step:
- **contact:** both feet on the ground, front heel down, arms at the extremes of their swing;
  the most spread pose;
- **down:** the weight lands on the front leg, which bends; the body is at its lowest; the arms
  are at their widest (a frame after contact);
- **passing:** the standing leg is straight under the body, the other leg passes it with the
  knee bent; the arms pass the body;
- **up:** the standing leg pushes up on the toes; the body is at its highest, about to fall into
  the next contact.
Every personality in a walk comes from changing these: how deep the down, how high the up, how
long the stride, where the weight is, what the arms and head do, the timing (a "double bounce"
walk, a sneak, a strut, a tired shuffle). Williams: vary the timing of parts. The head lags the
body; the hips lead.

## 4. Japanese practice, and what Ghibli's timing actually is
- **Drawing on ones, twos, threes** (1コマ打ち, 2コマ, 3コマ): each drawing held for 1, 2 or
  3 frames of 24. TV anime moved toward threes for economy ("limited animation", after Tezuka's
  *Astro Boy*); Ghibli's feature work uses all three, chosen per action.
- **Tame and tsume (タメ・ツメ):** *tame* is holding back, the pause or slow build before a
  release; *tsume* is the compression of spacing, drawings bunched toward a key so the motion
  snaps into it. Together they make the rhythm of Japanese animation (slow → snap → settle)
  distinct from Western even easing.
- **Ma (間):** meaningful pauses; the held pose (Brooks 2022; see `../characters/ghibli_style.md`).
- **Otsuka and Miyazaki:** Yasuo Otsuka (1931–2021), trained under Yasuji Mori at Toei in
  relatively full animation, taught Miyazaki and Takahata. His emphasis was weight, force and
  precise timing, and characters doing real work with real objects. Miyazaki's running notes
  (Animation Obsessive) give 4-, 6- and 8-drawing cycles chosen by character.

**Measured** (`tools/charref/drawing_rate.py` over the local Ghibli key-animation clips; share of
screen time by how long each drawing is held, static-camera clips only; the data is in
`data/drawing_rate.json`):

| | ones | twos | threes | 4–5 | holds 6+ |
|---|---|---|---|---|---|
| walk cycles (72 clips) | 21% | 24% | **42%** | 1% | 12% |
| character acting (154) | 19% | 32% | **35%** | 2% | 12% |

Caveats: compression noise can split a held drawing (inflating ones), and camera moves and
effects overlays count as change; clips that were mostly ones (pans) are excluded. The shape of
the result is clear, though: **Ghibli walks and acting are mostly on threes and twos, with about
an eighth of the time in held poses.**

**For us:** poses are sampled at a per-action drawing rate (threes for ordinary walking and
gestures, twos for brisker action, ones for fast action and for the camera-relative case where
stepping would read as lag), with real holds. This has to be tested in the game: a first-person
camera moving smoothly past characters drawn on threes is untried, and the rate may need to rise
with the character's screen speed.
