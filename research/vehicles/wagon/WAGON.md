# The station wagon: package, doors, frunk, lamps, styling

The first car built to the modular rules (see [../MODULAR_VEHICLES.md](../MODULAR_VEHICLES.md)). It is a
five-seat estate on the **Carrow Keel K-28** board, built to the class standard **SW180**, so a wagon from
any maker on a 2.8 m car board takes these doors, lids, glass and panels.

Coordinates are Blender's: X right, Y forward, Z up, in metres. z = 0 is the ground; y = 0 is midway
between the axles.

## 1. The board (fixed)

| | |
|---|---|
| board | Carrow Keel K-28 |
| length | 4.40 (±2.20) |
| width | 1.80 |
| wheelbase | 2.80 (axles at y = ±1.40) |
| track | 1.56 |
| wheel radius | 0.32 |
| deck top | z = 0.50 |
| mount rails | x = ±0.60, pitch 0.75 |
| drive | both axles; motors in the wheel pods |

There is no engine. Everything between the front wheels above the deck is free, so it becomes the
**frunk**.

## 2. The cabin: sized for our tallest people

**Characters:**
- stature ~ N(1.63, 0.07), clamped to [1.40, 1.95];
- men +0.13 m, so the tallest is about 2.08 m.

**Sitting height** is about 0.52 × stature, measured from the seat to the top of the head. For 2.08 m that is
1.08 m. The H-point (the hip joint) is about 0.10 m above the compressed cushion. With the back at 20°,
the H-point to the top of the head is about 1.00 m.

**Headroom.** Production cars give the 95th-percentile man (1.86 m) 25–60 mm. The user asked for "headroom
to spare" for *our* tallest:

- **H61** (H-point to the headliner) **≥ 1.15 m**. That is 150 mm over a 2.08 m man and 260 mm over the
  average man (1.76 m).

| SAE J1100 | front | rear | why |
|---|---|---|---|
| floor (heel) z | 0.55 | 0.55 | deck 0.50 plus a 0.05 floor |
| H30 (H-point above the heel) | 0.30 | 0.32 | a little higher than a sedan (0.27): easier ingress (Shino 2016) |
| H-point z | 0.85 | 0.87 | |
| back angle | 20° | 22° | |
| H61 headroom | 1.15 | 1.13 | |
| headliner z | 2.00 | 2.00 | a flat wagon roof keeps it over the rear seats too |
| roof skin z | 2.05 | 2.05 | |
| L53 / couple distance | | 0.88 | rear H-point 0.88 m behind the front |
| H-point y | 0.18 | −0.70 | front pedal heel at y ≈ 1.05, behind the front wheel pod (pod back edge at 1.04) |

**The wagon is tall: 2.05 m.** The skateboard puts the floor at 0.55 m, against 0.30–0.35 in a car with a
floor pan, and our people are tall. So this is a tall estate in the line of the Renault Espace, Nissan
Prairie and Mitsubishi Space Wagon, or today the VW ID. Buzz (1.94 m) and Hyundai Ioniq 5 (1.6 m on a
low floor). The styling (section 6) keeps it from looking like a van: a wedge nose, a long glasshouse, a
floating roof and a low belt.

**Width:**
- body 1.86 (outer half width 0.93), so the mirrors stay within the board's 1.80 plus the lane margin;
- cabin 1.70 at the belt (inner half width 0.85), 1.52 at the shoulder (tumblehome);
- shoulder room 1.45 front and rear.

## 3. Length plan (y)

| y | what |
|---|---|
| +2.28 | nose: a crush moulding, 8 cm past the board cap |
| +2.20 … +1.08 | **frunk** between and ahead of the front wheel pods |
| +1.08 | dash bulkhead and cowl; frunk lid hinge line |
| +1.15 (z 1.10) → +0.42 (z 1.96) | windscreen, raked 40° from vertical |
| +1.00 … +0.02 | **front door aperture** (0.98 wide) |
| +0.02 … −0.12 | B-pillar (thin, blacked out: the floating roof) |
| −0.12 … −0.96 | **rear door aperture** (0.84), ending 2 cm clear of the rear arch |
| −1.40 ± 0.42 | rear wheel arch (arch_half 0.42 = r + 0.10) |
| +1.40 ± 0.42 | front arch: the front door starts 2 cm behind it at +1.00 |
| −0.96 … −2.30 | load floor, 1.34 long behind the rear seat back at the floor (1.05 behind it at the belt) |
| −2.36 | tail; **hatch** hinged at the roof's rear edge |

Overall length 4.64, overhangs 0.88 front and 0.96 rear.

**Door aperture heads.** The ingress research (research/animation/car_ingress_egress.md) shows the duck is set by
the door head against the head's path, not by the headliner. The heads are at **z 1.90** front and rear,
with the sill top at **0.58**. That is a 1.32 m clear opening, the same as Okane's "high" mini-van mock-up
(1.50 m from the ground at a 0.24 m floor). Our tall people still duck a little: they are 2 m tall.

## 4. Doors, hatch and frunk lid (all work)

| closer | hinge | opens | travel | notes |
|---|---|---|---|---|
| front doors | front edge (A-pillar), vertical axis tilted 2° in at the top | out | 0 → 68° | detents at 35° and 68° (people open to 30–45° to get in) |
| rear doors | front edge (B-pillar) | out | 0 → 70° | as the front |
| hatch | rear edge of the roof, axis across the car | up | 0 → 88° | gas struts; the lower edge rises to about 2.0 m when open, clear of heads under 1.95 m. The bumper is the sill: load lip 0.62 |
| frunk lid | rear edge, at the cowl (y 1.08), axis across | front edge up | 0 → 60° | a short alligator; struts. Short lid: 1.0 m long, 1.30 wide |

**Animation** follows tram_section.gd's leaves: an eased angle per closer that snaps to its exact ends.
A door is opened by the hand (the ingress animation drives its angle). The hatch and lid run on their own ease:
0.9 s up, 0.7 s down.

**Seal.** Each closer's leaf carries its own outer skin, its own inner trim panel and its own reveal
round its glass. Every aperture has a body reveal joining the two shells (the RT255 rule). When closed, the
leaf's outer edge lies on the aperture's edge within the panel gap (4 mm, drawn closed: zero-gap rule),
so the seal test counts the closed leaf as part of both shells.

**No jamming** (the user's rule): a bent frame never locks a door. Hinges follow the frame joints. The
leaf may poke into the panel, but it always swings.

**Modular keys.** The interface is `SW180/<role>/<slot>/<side>`:
- `door_leaf/front/R`, `door_leaf/rear/L`;
- `hatch/rear/C`, `frunk_lid/front/C`;
- `glazing/screen/C`, `glazing/quarter/R`, …
Any SW180 wagon's front door fits any other SW180 wagon, whatever its style: same aperture, hinge
points and latch point. Styles differ in skin shape inside the envelope, trim and colour.

## 5. The frunk

There is no engine and no radiator. The front wheel pods hold the motors, and the bus socket is behind
the front axle on the centre line.

- **Tub:** a moulded liner on the deck from y 1.10 to 2.12, between the pods' inner faces (x ±0.47) aft of
  y 1.75, widening to ±0.70 ahead of the axle.
- Its floor is at z 0.55. The lid top sits at about z 1.02 at the cowl and 0.92 at the nose.
- **Volume** is about 0.30 m³ less the tub walls: **about 150 L**. Tesla Model Y holds 117 L, a Taycan 84 L,
  and an F-150 Lightning 400 L.
- The **hood is short**: the cowl at y 1.08 is 1.20 m from the nose, against about 1.6 m on the old cream
  wagon. The windscreen base moves forward, so the glasshouse is long.
- Inside: a lamp, a drain, two bag hooks.
- The bumper beam and the crush moulding are in front of the tub (the crash structure the engine used to be).

## 6. Lamps (working)

### Projector headlamps
A projector is a sealed unit:
1. an **ellipsoidal reflector** with the source (LED) at its first focus;
2. a **cutoff shield** at the second focus, which makes the sharp horizontal cut;
3. an aspheric **condenser lens** that throws the shield's edge onto the road.

The low beam's cut-off is flat on the oncoming side and steps up 15° on the kerb side. We drive on the
right, so the step goes up on the right.

**In the game:**
- one `SpotLight3D` per lamp, angle 28°, range 45 m (low) or 90 m (high);
- `light_projector` set to a cut-off texture: dark above the cut, the 15° step on the right, a hot spot
  just below and right of centre;
- shadows only on the player's own car;
- the lens itself is an emissive disc with a bright core ring (the projector "eye"), plus the
  sidelight ring (DRL) round it.

**Look:** two **round projector eyes** each side, set in a dark full-width glass band across the nose: the
retro round lamps behind a futurist band.

### Taillights
- One full-width **light bar** across the hatch: a row of square pixels (the Ioniq 5 "parametric pixel",
  after the 1974 Pony).
- **Tail:** low red emission. **Stop:** ×4 emission plus an `OmniLight3D` (red, range 3 m). Reverse: two white
  pixel blocks with a `SpotLight3D` (range 8 m) when reversing. Indicators: amber pixel ends, flashing at 1.5 Hz.
- The **lamp units are components** (`head_lamp/front/R`, `tail_lamp/rear/C`) with their light markers
  (position, direction, kind) in the blueprint, so a different maker's lamp fits the same slot and the
  game puts the lights on its markers.

## 7. Styling: retro, futurist

The user asked for "more futuristic but still retro". The world: 1970s retro-futurist industrial design,
fully electric, cottage-built on a tube frame. Flat and single-curved panels suit hand-made tube-frame
bodies (TVR, Lotus, Reliant).

**Sources:**
- Retro estates: Citroën CX Break and GS Break (1970s, long glasshouse, single-spoke futurism); Volvo 1800ES
  and Reliant Scimitar GTE (shooting brakes with glass tailgates); Lancia Beta HPE; AMC Pacer wagon.
- Retro futurism: Giugiaro's 1974 Hyundai Pony, and its descendant the Ioniq 5 (parametric pixels,
  faceted "Z" flank crease); Bertone's wedges (Carabo, Stratos Zero); GM Aerovette; Ford Probe I; the
  Renault Espace (1984), the first tall one-box. Today's echoes: VW ID. Buzz, Renault 5 E-Tech, Honda e,
  Lancia Pu+Ra HPE, Citroën Oli.
- driventowrite.com on retrofuturism: wedge geometry and faceted panels against 1970s boxy wagons with chrome.

**The design.** It follows the Grok references already made for the catalogue's station wagon
(`reference/grok/station_wagon/`: side, three_quarter, front, rear; the user, 2026-10-02: "use the reference images we
already had grok make"). They show a 1970s American estate in cream: woodgrain side panels framed in chrome below
the belt, a chrome belt line, cream pillars with chrome window surrounds, roof rails, a woodgrain lower hatch panel,
and stacked rectangular lamps. We keep all of that and make it futurist:

| from the references (retro) | made futurist |
|---|---|
| long bonnet over an engine | a **short wedge bonnet** (the frunk lid) running into a **steeply raked windscreen**; the glasshouse grows forward |
| chrome grille and quad lamps | no grille (electric): a cream nose with a **dark full-width glass band** holding **two round projector eyes** each side, ringed in chrome |
| woodgrain panels in chrome frames | kept, **one woodgrain inlay per panel** (each door, each quarter, the hatch), framed in chrome, stopping at every shut line and arch (the no-trim-across-openings rule) |
| chrome belt and window surrounds | kept, along each panel's own edges; the glass **flush** with the body |
| stacked red tail lamps | a **pixel tail bar** in each tail corner (rows of small square red lamps) |
| chrome hubcaps, whitewalls | **turbine wheel covers** ("phone dial" aero discs) on whitewalls |
| roof rails | kept |
| tall upright cabin | taller (2.06 m: the skateboard floor and our tall people), so the cream roof and a low chrome belt keep it long-looking |

No exhaust or fuel cap; a charge flap on the right rear quarter.

## 8. Ingress package checks
- Door opening at 35°, the ingress pose: the clear gap from the door's inner trim to the B-pillar is ≥ 0.62 m
  (Okane's mock-up: 950 mm doorway at 30°).
- Sill: 0.58 high (deck 0.50 plus sill), 0.12 wide. The knee lift for the step (hip 80°) clears it.
- Head path: the animation's duck clears the door head at z 1.90 for every stature, by IK on the neck and trunk.
- Grabs: an A-pillar grab, a roof-rail grab over each door, and a B-pillar handle low at 1.15 m. Choi 2009:
  a low B-pillar handle eases egress.
