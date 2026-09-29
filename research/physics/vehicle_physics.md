# Vehicle physics: BeamNG, Gran Turismo, Forza, and what we took (2026-09-28)

## BeamNG.drive: soft-body, node-and-beam
Each vehicle is a mass-spring network. **Nodes** are point masses. **Beams** are damped springs
between two nodes, and they can deform (bend permanently) and break. Collisions are node-to-triangle
against the vehicle's own skin and the world. Everything is explicit integration, which is why the
simulation has to step very fast.

| Quantity | Value | Source |
|---|---|---|
| Physics rate | **2000 Hz** (0.5 ms steps) | BeamNG physics page; Wikipedia |
| `nodeWeight` default | **25 kg** (as of 0.39.1.0) | JBeam nodes doc |
| `frictionCoef` default | **1.0**; commonly 0.5 on body nodes | JBeam nodes doc |
| `beamSpring` default | **4,300,000 N/m** | JBeam beams doc |
| `beamDamp` default | **580 N·s/m** | JBeam beams doc |
| `beamDeform` default | **220,000 N**: the force at which a beam starts to deform plastically | JBeam beams doc |
| `beamStrength` default | **FLT_MAX** (unbreakable unless set) | JBeam beams doc |
| `beamPrecompression` default | 1.0 | JBeam beams doc |
| Suspension spring (typical) | spring 40,000 N/m, damp 0 | JBeam examples |
| Dampers (typical) | spring 0, damp 4,500 N·s/m | JBeam examples |
| Body structure (typical) | spring 8,000,000 N/m, damp 125 | JBeam examples |
| Steering rack | spring 14,001,000 N/m, damp 250 | JBeam examples |

Beam types: NORMAL, SUPPORT (acts only in compression), HYDRO (steering and actuators),
ANISOTROPIC (separate compression and extension), BOUNDED (limited travel, used for shocks),
L-BEAM, and PRESSURED (tyres).

Damage comes from plastic deformation. A beam loaded past `beamDeform` takes a permanent new rest
length; past `beamStrength` it breaks. Damage therefore grows with the collision energy, and
nothing is scripted per car.

## Forza Motorsport (2023)
- The new tyre model samples **8 contact points per tyre at 360 Hz**. Forza Motorsport 7 used
  1 point at 60 Hz. Turn 10 calls this **48×** the detail (8 × 6).
- It adds tyre compounds and tyre wear, plus environmental factors (track temperature and rubbering-in).
- Physics runs at 360 Hz independent of the frame rate. Damage is mostly cosmetic and mechanical;
  the chassis isn't a soft body.

## Gran Turismo (Polyphony Digital)
- One unified physics model for every car, with **"several thousand parameters"** per car
  (Kazunori Yamauchi's lecture).
- The tyre model has been validated against real lap times since 2007. Aero maps come from CFD plus
  wind-tunnel data. Michelin is a technical partner; GT7 later added a Dunlop partnership.
- Polyphony has **not published** a physics tick rate. GT7 update 1.31 added a 120 Hz display
  mode, and update 1.49 revised the physics (tyres and suspension). In 2026 Yamauchi still calls
  tyre physics GT's biggest challenge.
- Damage is light (mechanical and visual). GT doesn't model crash deformation.

## Crash thresholds from the real world
| Test | Speed | What it means |
|---|---|---|
| FMVSS 581 (US bumper standard) | 2.5 mph (4 km/h) | no damage to safety parts: a nudge |
| **RCAR bumper test** (since 2010) | **10 km/h** (also 5 km/h) | where bumpers have to start absorbing: a real knock |
| **RCAR low-speed structural test** | **15 km/h**, 40 % overlap, 10° barrier; a 1400 kg barrier into the rear at 15 km/h | where the structure starts taking repairable damage |
| 14 CFR 23.473 (light aircraft landing gear) | descent velocity 4.4 (W/S)^¼ ft/s, **7–10 ft/s** (2.1–3.05 m/s) | what landing gear has to absorb: a touchdown this fast is a landing, not a crash |

## What the game does (air_vehicle.gd, ground_vehicle.gd)
Our vehicles are kinematic, swept against the world every physics tick at 60 Hz. BeamNG's
node-and-beam model at 2000 Hz is far beyond the budget of GDScript on a Steam Deck. From these
sources we took the thresholds and the energy scaling:

- **Crash sound** at an impact speed into the surface of **≥ 10 km/h** (RCAR bumper test), for
  every vehicle. Its volume and pitch scale with speed from 10 to 60 km/h. The sound is synthesised
  by `tools/crash_sound.py`: a thump, a metal crunch from sheet-metal modes, a scrape and debris.
- **Aerostat crash physics only**:
  - a rebound with restitution 0.35;
  - an angular impulse from the off-centre hit, ω ≈ (r × n) · v(1+e)/k² with k ≈ 2 m, damped ×0.25
    for the air the envelope pushes. Its yaw part turns the aerostat; its tilt part sets the cabin
    swinging as a damped pendulum under the balloon (ω₀ = √(g/3 m) ≈ 1.8 rad/s, ζ = 0.25, capped at 40°);
  - loss of control for 0.3–3 s;
  - **structural damage above 15 km/h** (RCAR structural test), scaled by energy like BeamNG's
    plastic deformation: damage % = 100 · (v² − 15²)/(60² − 15²) with v in km/h. A 30 km/h hit
    costs 20 %, 45 km/h costs 53 %, 60 km/h wrecks it. A damaged hull flies slower (40–100 % of top
    speed). At 0 % the aerostat is disabled: the fans stop, the balloon slackens and it sinks at 2 m/s.
  - a touchdown on the casters at up to **3.05 m/s** (10 ft/s, 14 CFR 23.473) is a landing. Full
    descent (5 m/s = 18 km/h) into the ground is a crash, so slow down before landing.
- Trees are solid: a trunk cylinder and a canopy sphere each, within 140 m of the player
  (MapTrees.gd).

## Sources
- BeamNG physics: https://beamng.com/game/about/physics/
- JBeam beams: https://documentation.beamng.com/modding/vehicle/sections/beams/
- JBeam nodes: https://documentation.beamng.com/modding/vehicle/sections/nodes/
- JBeam intro: https://documentation.beamng.com/modding/vehicle/intro_jbeam/
- BeamNG.drive (Wikipedia): https://en.wikipedia.org/wiki/BeamNG.drive
- BeamNG 0.35 strength and JBeam updates: https://www.overtake.gg/news/beamng-drives-0-35-vehicle-strength-and-jbeam-updates-bolster-playability.3075/
- Forza Motorsport's new tyre model: https://www.gtplanet.net/forza-motorsport-new-tire-model-20210528/
- Forza Motorsport physics changes: https://www.operationsports.com/forza-motorsport-to-feature-major-physics-changes-tire-compounds-and-environmental-factors/
- Forza Motorsport, generational leap: https://www.techradar.com/news/forza-motorsport-is-a-huge-generational-leap-from-previous-games-heres-why
- Yamauchi's lecture on GT's driving physics: https://www.gtplanet.net/dr-kazunori-yamauchi-gives-lecture-gran-turismos-driving-physics-production/
- GT7 update 1.31 (120 Hz, physics): https://www.gtplanet.net/gran-turismo-7-update-1-31-details-120hz-vrr-new-cars-events-track-layouts-physics-changes-and-more/
- GT7 update 1.49 physics: https://www.autoevolution.com/news/how-gran-turismo-7-s-update-149-improves-the-car-physics-simulation-model-237495.html
- Tyre physics remain GT's biggest challenge (2026): https://www.gtplanet.net/kazunori-yamauchi-says-tire-physics-remain-gran-turismos-biggest-challenge-20260822/
- Michelin and Gran Turismo: https://michelinmedia.com/gran-turismo/
- RCAR low-speed structural crash test protocol, Issue 2.4: https://www.azt-automotive.com/_Resources/Persistent/cc71045e21b31eaad9e08cd62ddb33e95e77a758/RCAR%2015%20km-h%20test%20procedure%20Version%202_4.pdf
- RCAR standards: https://www.rcar.org/published-works/rcar-standards-papers
- 14 CFR 23.473: https://www.govinfo.gov/app/details/CFR-2016-title14-vol1/CFR-2016-title14-vol1-sec23-473
