# Getting into and out of a car

How people actually get into and out of a car seat, written so that our pose-based animator
(see [motion_design.md](motion_design.md)) can do it for every body we generate, timed with the door.
It is researched for the station wagon (`research/vehicles/wagon/`) and applies to every car-class
vehicle.

## Sources

**Motion-capture studies:**
- **Ait El Menceur et al. 2008**, *Applied Ergonomics*. Ingress and egress by young, elderly and disabled
  drivers, for four car types. sciencedirect.com/science/article/pii/S0169814108000632
- **Choi et al., ISB 2009**. Egress kinematics and joint loads, and the effect of the B-pillar handle.
  media.isbweb.org/images/conf/2009/data/pdf/167.pdf
- **Okane et al. 2024**, *Advances in Human Factors of Transportation* 148:344. Gaze and whole-body
  movement during ingress, at roof heights of 1.50 and 1.33 m. doi 10.54941/ahfe1005225.
  - The mock-up: sill 160 mm above the floor; floor 240 mm off the ground; seat (H-point) 355 mm above the floor.
  - The door opening: 950 mm wide, opened to 30°.
- **Auburn University / Hyundai-Kia, Xsens MVN**: 93 participants, ingress and egress durations by group.
  xsens.com/cases/analysis-vehicle-ingress-egress and doi.org/10.1080/23335432.2020.1716847
- **Causse et al. 2011/2012**. How roof height affects the strategy. They also built the mock-up
  dimensions that Okane uses.
- **SAE 2007-01-2493**. A database of about 900 ingress and egress motions by elderly people. Also
  SAE 2016-01-1433 and 2018-01-1321, which use touch points: hand-first and foot-first transfers,
  touching the seat and the steering wheel.

**Occupational therapy guidance** (the "sit-first" technique):
- HealthLinkBC and Kaiser Permanente, *Mobility problems: getting in and out of a car safely*.
- Uber Health (a physical therapist): uberhealth.com/us/en/resources/articles/how-to-enter-and-exit-car/
- Toyota UK with the Royal College of Occupational Therapists, demonstrated in an Aygo X and a
  **Corolla Touring Sports (an estate)**: mag.toyota.co.uk/royal-college-of-occupational-therapists/

**Videos:**
- "Car Etiquette 101: How to Enter & Exit a Car Elegantly", youtube.com/watch?v=5XF1yXlLknI. Sit-first
  with the knees together, the "elegant" variant; it covers a sedan and an SUV.
- "DRIVING - Getting Into Your Vehicle", youtube.com/shorts/xfPw4Aic-kE. A therapist's technique for
  sparing the back.
- The Toyota/RCOT demonstrations (above).
- The ISB and Xsens pages carry motion-capture stills.
- I couldn't watch footage frame by frame. The key poses below come from the stills, figures and
  descriptions in these sources, cross-checked against each other.

## What people do

### Two strategies (Ait El Menceur 2008; SAE touch-point studies)

| strategy | share | sequence |
|---|---|---|
| **one-foot, "swing in"** | 79% | Stand beside the door, facing forward. Put the inner foot in, onto the floor by the pedals. Duck the head and swing the torso in while the outer foot pivots on the ground. Drop onto the seat. Bring the outer foot in. |
| **two-foot, "sit first"** | 21% (most of the elderly; what therapists teach) | Turn your back to the seat. Lower your bottom onto it. Swing both legs in together, knees together. |

- The **head-first** variant leans the torso in early: younger people and low roofs.
- The **hip-first** variant leads with the bottom: older people and high seats.
- Okane's gaze groups match these:
  - group 2 looks at the floor and bends forward the most (head + hip angle about 55–65°);
  - groups 1 and 3 look into the cabin or at the door and stay upright (about 20–35°).
- Familiarity matters: on first use people watch the roof and the sill; once they know the car, they stop looking.

### Ingress phases (driver's side, left-hand drive; mirror for the right side)
1. **Approach and open** (0.6–1.0 s). Walk to the door hinge-side-last, so you arrive at the B-pillar end of the
   opening. Reach the handle and pull the door out to about 30–45°, stepping back as it swings.
2. **Step in** (about 0.5 s). Turn the body about 60° toward the seat. Lift the inner (right) knee high, at about
   70–90° of hip flexion, to clear the sill, and put the right foot on the floor ahead of the seat.
   One hand on the roof rail or the A-pillar grab, the other on the door top or the wheel.
3. **Duck and transfer** (about 0.8 s). This is the hardest phase.
   - Flex the neck about 20–40°. Tuck the head under the door head and lean the trunk about 20–30°
     toward the cabin.
   - The outer foot pivots, and the pelvis rotates about 90° in total.
   - Lower the body onto the seat. The weight moves from the outer leg to the seat.
4. **Bring the leg in** (about 0.5 s). Abduct and flex the left hip to lift the left foot over the
   sill. The left knee is the last thing in.
5. **Settle** (about 0.4 s). A small bounce, square the shoulders, hands to the lap or the wheel.
6. **Close** (about 0.4 s). Reach out to the door pull and swing it shut.

### Egress phases (more complex than ingress: Choi 2009; Xsens)
1. **Open** (about 0.4 s). Inner hand on the door release, push the door to 30–45°.
2. **First leg out** (about 0.6 s).
   - Rotate the pelvis about 45° toward the door.
   - The outer (left) leg goes out first, over the sill, with the foot planted on the ground beside the car.
   - The hip abducts the most here: the joint stress peaks.
3. **Rise** (about 0.9 s).
   - Hold the door frame, B-pillar or roof rail. A lower B-pillar handle reduces joint stress.
   - Lean forward, nose over the knees, push up, and duck under the door head.
4. **Second leg out** (about 0.5 s). The inner leg swings over the sill. In the study's measure, egress
   ends when the second leg crosses the sill.
5. **Step clear and close** (about 0.6 s). One step away along the car, turn, and push the door shut.

### Durations (Xsens / Hyundai-Kia, 93 participants)

| group | ingress | egress |
|---|---|---|
| control | 2.97 s | 2.95 s |
| high BMI | 2.71 s | 4.42 s |
| elderly | 4.33 s | 5.26 s |

These cover the transfer only. Opening and closing the door add about 1 s each.

### What changes it
- **Roof and door-head height.** Lower roofs mean more neck and trunk flexion and more head-first entries
  (Causse; Okane). Our wagon is tall (section *Package*), so most of our people go in fairly upright.
- **Seat height.** A higher seat makes it shorter and easier, especially for the elderly (Shino 2016).
- **Sill width and height.** These set how high the knee lifts.
- **Handles.**
  - People grab the A-pillar, the roof rail, the door top, the seat bolster and the steering wheel.
  - Therapists say never use the door as the main support, because it moves.
- **Passenger seats**: there is no wheel to grab, so people use more seat and roof-rail holds.
- **Rear seats** have the narrowest openings, so people duck more and use more of the sit-first strategy.

## How we animate it

The motion is pose-based, following the animator's rules: key poses with timing and spacing, IK for the hands and
feet, and no foot sliding. The vehicle's blueprint gives every seat a **station**:
- `door`: the leaf and its hinge;
- `stand`: the outside foot target, beside the B-pillar end of the opening;
- `seat`: the H-point, with the back angle;
- `heel`: the floor point the inner foot lands on;
- `grab`: the hand holds (A-pillar or B-pillar grab, roof rail, wheel rim, seat bolster).

Each person picks a **strategy** from who they are:

| who | strategy |
|---|---|
| elderly (age > 65), injured, or a high BMI | **sit-first**, slow (×1.4–1.8) |
| tall (seated head within 6 cm of the door head) | **one-foot, head-first**, a deep duck |
| everyone else | **one-foot**, hip-first or head-first at random (60/40), with the personality's tempo |

Laban Effort (from the Big Five, see expressive_motion.md) scales the tempo:
- sudden, direct people drop into the seat;
- sustained ones lower themselves.

### Key poses, one-foot ingress (times for a control adult; scaled per person)

| t (s) | pose | contacts |
|---|---|---|
| 0.00 | standing at `stand`, facing forward, hand at the handle | both feet |
| 0.45 | door at 40°; body turned 60° toward the seat; weight on the outer foot | outer foot; hand on the door |
| 0.90 | **step**: inner knee up (hip 80°), inner foot over the sill onto `heel`; free hand on the roof rail or A-pillar | both feet; roof hand |
| 1.50 | **duck**: neck 30° flexed, trunk leaning 25° in, pelvis turned 80°, knees bent, hips over the seat edge | both feet; roof hand; seat-bolster hand |
| 1.90 | **seated, leg out**: weight on the seat; the outer leg still outside, foot on the ground | seat; both feet |
| 2.40 | **leg in**: outer knee raised and abducted, foot over the sill | seat; inner foot |
| 2.80 | **settled**: upright, hands to the lap or the wheel; a small bounce | seat; both feet |
| 3.20 | reach to the door pull; the door closes over 0.4 s | |

Sit-first ingress:
- 0.0 stand → 0.6 turn your back to the seat, hands on the roof rail and the seat;
- 1.4 lower to the seat edge;
- 2.0 slide back;
- 2.8 swing both legs in together, knees together, pivoting on the bottom;
- 3.4 settled.

Egress is roughly the reverse of the one-foot ingress, with its own timing:
- 0.0 seated → 0.4 door open;
- 1.0 outer leg out, planted;
- 1.9 **rise**: lean forward, hand on the B-pillar or roof rail, duck;
- 2.4 standing, half out, inner foot still inside;
- 2.9 inner leg out;
- 3.5 step clear, turn, push the door shut.

### Rules
- **Never pass through the body.** The duck is the clearance. The head's path is checked against the door
  head and the roof rail. If it would hit, increase the neck flexion (up to 45°) and the trunk lean, then
  slow the step. That is our "tall people duck more".
- **The door is part of the motion.** It opens before the step and closes after settling. The hand stays on the
  pull while it moves, and the door's angle is driven by the hand, not on its own timer.
- **The feet are planted.** The outer foot pivots in place, so turn on the ball of the foot: no sliding.
- **The camera for the player.** The same poses play in first person, so the camera rides the head bone:
  - it dips as the head ducks;
  - it clamps 6 cm inside any panel while the head is in the door opening.
- **Interrupts.** If a person is pushed during the transfer, finish to the nearer of "seated" and
  "standing outside". Never leave someone half in the car (the user's rule: never stuck in a vehicle).
- **Passengers** use the same poses, with the seat-bolster and roof-rail grabs in place of the wheel.
- **Rear seats** add 15% to the duck and use the B-pillar grab.
