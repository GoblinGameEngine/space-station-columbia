# Expressive motion: how movement carries personality and emotion

## 1. Laban Movement Analysis
Rudolf Laban (1879–1958; *The Mastery of Movement*, 1950) and his students built a vocabulary for
movement quality used in dance, drama, therapy and ergonomics. It has five components: Body,
Space, **Shape**, **Effort**, Relationship.

**Effort** has four factors, each a continuum between an *indulging* pole and a *condensing*
(fighting) pole:

| factor | indulging | condensing | examples |
|---|---|---|---|
| Space (attention) | Indirect: flexible, multi-focus | Direct: single focus | waving away insects / threading a needle |
| Weight (impact) | Light: buoyant, delicate | Strong: powerful, pressing | describing a feather / pushing a heavy object |
| Time (urgency) | Sustained: lingering | Sudden: hurried | stroking a pet / swatting a fly |
| Flow (control) | Free: abandoned, hard to stop | Bound: controlled, able to stop | shaking off water / carrying hot liquid |

**Shape** has three dimensions: Horizontal (Spreading ↔ Enclosing), Vertical (Rising ↔
Sinking), and Sagittal (Advancing ↔ Retreating). Spreading has an affinity with Indirect, Rising
with Light, and Advancing with Sustained.

## 2. EMOTE: Effort and Shape as animation parameters
Chi, Costa, Zhao & Badler, "The EMOTE Model for Effort and Shape" (SIGGRAPH 2000) [local]:
Effort and Shape applied on top of any underlying movement.
- **Arms:** keypoint paths are interpolated with Kochanek–Bartels splines. Tension sets how
  sharply the path bends at a key, continuity sets the tangent break, and bias sets overshoot or
  undershoot. Timing is controlled by anticipation, overshoot, the inflection time and a time
  exponent. There are also wrist bend and extension, and arm and elbow twist, with frequencies.
  Example: Strong adds anticipation (the hand pulls back before extending).
- **Torso (Shape):** the Vertical dimension goes to the neck and spine, Horizontal to the
  clavicles (a little pelvis), and Sagittal to the pelvis (a little neck and spine). Each pose's
  angles get the weighted maximum displacement for Spreading, Enclosing, Rising, Sinking,
  Advancing and Retreating. In their words, Shape "essentially provide[s] squash and stretch
  within the limits of a fixed segment length articulated skeleton."

## 3. PERFORM: from the Big Five to motion (the numbers)
Durupinar, Kapadia, Deutsch, Neff & Badler, "PERFORM: Perceptual Approach for Adding OCEAN
Personality to Human Motion using Laban Movement Analysis" (ACM TOG) [local].
- A Laban expert defined motion parameters for each Effort combination ("Drives").
- Crowd-sourced studies (244 participants) measured which Efforts people read as which
  personality.
- A regression maps Efforts to motion parameters.

**Step 1: Big Five → Effort.** The normalised Personality–Effort matrix, with Effort in [−1, 1]
and **negative = the indulging pole** (Indirect, Light, Sustained, Free); personality P in [−1, 1]:

| Effort \ Personality | O | C | E | A | N |
|---|---|---|---|---|---|
| Space | −0.921 | 0.928 | −0.894 | 0 | −1 |
| Weight | 0 | 0 | 0 | −1 | 0 |
| Time | 0 | −0.857 | 0.99 | −1 | 0.97 |
| Flow | −0.931 | 0.938 | −1 | 0 | −0.762 |

E_i = max over j of the positive products NPE(i,j)·P(j) + min over j of the negative products
(a strongest pull each way, rather than a plain sum).

Read in words:
- open people move Indirect and Free;
- conscientious people move Direct, Sustained and Bound;
- extroverts move Indirect, Sudden and Free;
- agreeable people move Light and Sustained;
- neurotic people move Indirect, Sudden and Free.

(The paper's own example text calls agreeable "Strong", but the table and study ratios, 0.631
choosing Light, say Light. We follow the data.)

**Step 2: Effort → motion parameters** (Table IV, a multivariate linear regression:
parameter = intercept + a·Space + b·Weight + c·Time + d·Flow). The ones we can use:

| parameter | intercept | Space | Weight | Time | Flow |
|---|---|---|---|---|---|
| animation speed | 0.558 | 0 | 0.001 | **0.470** | 0.001 |
| anticipation velocity | 0.223 | −0.011 | **0.297** | 0 | −0.029 |
| overshoot velocity | 0.344 | −0.042 | −0.042 | 0 | **−0.458** |
| anticipation time | 0.031 | −0.002 | 0.041 | 0.008 | −0.002 |
| overshoot time | 0.930 | 0.015 | 0.018 | −0.015 | 0.092 |
| time exponent (accel/decel) | 1.043 | 0.015 | 0.008 | 0.072 | 0.060 |
| wrist bend | 0.191 | −0.008 | **−0.238** | 0 | −0.025 |
| wrist twist | 0.160 | −0.010 | −0.053 | 0.010 | **−0.196** |
| elbow twist | 0.281 | −0.009 | 0.039 | −0.005 | **−0.313** |
| torso rotation magnitude | 0.290 | −0.043 | 0.040 | 0.010 | **−0.331** |
| torso rotation frequency | 1.283 | −0.179 | 0.223 | 0.067 | **−1.410** |
| head rotation magnitude | 1.210 | **−0.804** | 0.008 | 0.004 | −0.178 |
| head rotation frequency | 1.078 | **−1.225** | 0.104 | −0.017 | 0.184 |
| breathing magnitude | 0.641 | 0.015 | −0.123 | −0.010 | −0.063 |
| breathing frequency | 0.687 | −0.031 | 0.263 | −0.156 | −0.188 |
| enclosing/spreading (arms) | 0.195 | −0.003 | 0.164 | 0.001 | −0.365 |
| sinking/rising | 0.136 | −0.056 | **−0.819** | 0.014 | −0.125 |

Units are the paper's own (normalised). What we use is the direction and relative size.

Read in words:
- **Indirect** people look about more and more often (head rotation magnitude and frequency);
- **Free** people move the torso more and overshoot;
- **Strong** people anticipate and sink;
- **Sudden** people move faster.

Validation: with 55 participants, all five traits were recognised from motion (p < 0.001).
Extroversion and neuroticism were read best; openness and agreeableness least.

## 4. Emotion in the walk
- **Roether, Omlor, Christensen & Giese** (J. Vision 2009; thesis 2011 [local]). Emotion was
  expressed through gait, with speed-matched neutral walks as controls:
  - **Sadness:** strongly increased **head inclination** (the dominant feature), smaller
    movements, slow.
  - **Anger:** faster, **larger movements**, increased **elbow flexion**, strong arm movement.
  - **Happiness:** faster, larger movements than even a speed-matched neutral walk, big shoulder
    and elbow swing.
  - **Fear:** smaller movements, increased elbow flexion, **upper-arm retraction**, **knee
    flexion**.
  - Energetic (activated) affects give larger movements; deactivated ones give smaller. Speed alone
    does not explain the differences.
- **Troje** (J. Vision 2002; "Decomposing biological motion"): point-light walkers decompose into a
  few principal components. Gender, emotion and body-weight axes can be found and exaggerated
  (caricatures). Lateral body sway and the shoulder–hip relation carry gender. Johansson (1973)
  first showed that a dozen moving dots read as a person.
- **Unuma, Anjyo & Takeuchi**, "Fourier Principles for Emotion-based Human Figure Animation"
  (SIGGRAPH 1995) [local]: joint curves as Fourier series. A "briskness" difference between a
  normal and a brisk walk can be added to a run. Styles are differences in frequency space and
  superimpose.

## 5. Tension and relaxation
Neff & Fiume, "Modeling Tension and Relaxation for Computer Animation" (SCA 2002) [local]:
- muscle tension separates *stiffness* from *position*;
- a relaxed arm swings and settles (passive dynamics), while a tense one holds and moves stiffly;
- an antagonistic joint model gives both.

"AER: Aesthetic Exploration and Refinement for Expressive Character Animation" (SCA 2005):
- edits for aesthetic properties such as succession (motion flowing along the body from centre to
  extremities), balance, extent and amplitude.

**For us:** stiffness is a per-person, per-mood parameter on the springs (a tense or anxious
person has stiff, fast springs; a relaxed person has loose, low-frequency ones that swing and
settle).

## 6. Perlin's Improv: noise with personality
Ken Perlin, "Real Time Responsive Animation with Personality" (IEEE TVCG 1995), and Perlin &
Goldberg, "Improv" (SIGGRAPH 1996):
- joint angles are expressions of rhythmic and stochastic (noise) functions;
- blending actions by weights gives "the subjective impression of dynamics" without simulation;
- characters "appear dynamically balancing, nervous, or gesturing in particular ways" from
  tuned noise;
- Improv adds behaviour scripts that choose actions and blend them.

This is the direct ancestor of what we're building.

## 7. Idle, gaze, gesture
- **Idle** (Egges, Molet & Magnenat-Thalmann 2004): standing people make small posture
  variations plus occasional **balance shifts** (weight moving from one foot to the other), and
  these are personal. The timing between shifts varies.
- **Gaze** (Ruhland et al., "A Review of Eye Gaze in Virtual Agents…", CGF 2015):
  - the eyes lead and the head follows (large shifts combine a saccade with a slower head turn);
  - blinks accompany gaze shifts and are more frequent when speaking;
  - gaze is shared and averted in conversation according to turn-taking and personality.
- **Gesture:**
  - Kendon: a gesture has phases, preparation → **stroke** (the meaningful part, the most
    energy) → hold → retraction; all optional but the stroke.
  - McNeill (*Hand and Mind*, 1992): four types. **Iconic** gestures show shape or action,
    **metaphoric** gestures show abstract ideas, **deictic** gestures point, and **beats** mark the
    rhythm of speech.
  - BEAT (Cassell, Vilhjálmsson & Bickmore, SIGGRAPH 2001) [local] generates synchronised gesture,
    gaze and intonation from text by rules from conversation research.
  - Neff et al. (2008) model a speaker's personal gesture style statistically.

## 8. Perception
- Hodgins, O'Brien & Tumblin (1998): viewers discriminate motion differences better on more
  detailed (polygonal) bodies than on stick figures. The more solid our people look, the more
  errors show. Foot sliding and interpenetration will be noticed.
- McDonnell et al. 2008 (in `../characters/scale_survey.md`): motion clones are harder to spot
  than appearance clones, but per-person variation still matters in groups.
