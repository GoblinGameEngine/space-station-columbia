# Skateboard chassis: research and the station's boards (2026-10-01)

**The brief (the user, 2026-10-01):**
- All ground vehicles are built on skateboard platforms.
- The station's AI (the Steward) designs and makes its own board. It is sleek and organic and uses as little material as possible. It has never changed, and it carries the heavy vehicles.
- Three companies of the people make cruder derivatives for personal and passenger vehicles. Each is a tube frame carrying the motors, batteries and electronics, at the level of a mid-21st-century EV cottage industry run at scale.
- Every vehicle type should eventually be unique, generated on the fly, built of discrete interchangeable modules, and fully destructible. The bodies come next, inspired by the Grok designs.

**What exists:**
- The canon is in `tools/bible/canon_industry.py`, which builds `research/bible/12_industry.md`.
- The engineering numbers are in `tools/vehicles/platforms.py`, which builds `godot_project/remake/vehicles/chassis/platforms.json`.
- The models are built by `remake/blender/chassis/chassis.py` into `godot_project/remake/vehicles/chassis/*.glb`.
- The renders are in `research/vehicles/chassis_img/`; `_sheet.png` shows all six.

## 1. What a skateboard chassis is

A flat, self-contained rolling platform carries everything that makes a vehicle go: the battery, the motors, the suspension, the steering, the brakes and the controllers. The body (the "top hat") bolts on top and carries no drive components. The ideas that matter here:

| idea | where it comes from | what we take |
|---|---|---|
| **Everything in a thin floor; any body on top** | GM AUTOnomy / Hy-wire (2002): fuel cell, tanks and motor in a flat platform; "sedan, minivan or bus" on the same base; drive-by-wire; 3,114 mm wheelbase, about 1,814 kg | The Pattern: one body interface, so bodies are interchangeable |
| **Corner modules** | REE Automotive's REEcorner: motor, reduction, inverter, steer-by-wire actuator, double-wishbone suspension with twin dampers, brake actuators, sensors and an ECU **in each wheel's module**. The platform is flat, a module is swapped in about 20 min (plus about 40 min of calibration), and the P7-C runs at 16,000 lb GVWR | The Steward's **pods**: a whole drive corner per wheel, replaced by exchange at a Board Drop |
| **Body-on-skateboard, bolted and glued** | Rivian R1T: a quad-motor skateboard, one motor per wheel, 105–149 kWh, double wishbones / multi-link, air suspension; the body bolted and bonded, not welded | Bodies bolt to the mount rails |
| **Structural battery / cell-to-chassis** | Tesla's structural pack (cells bonded between sheets, tied into the gigacast underbody; AA 386 Al-Si casting, 55–61 MN presses); BYD CTB; cell-to-chassis designs | The Steward's spans **are** the pack: the cells are set in the structural lattice, sealed |
| **Generative / topology-optimised structure, printed** | Topology optimisation puts material only where the loads go and produces bone-like forms that suit additive manufacturing. Divergent / Czinger 21C (printed nodes, the BrakeNode). Wikipedia carries little detail, so this is from general knowledge | The Steward's look: a grown lattice of pale alloy, waisted struts and fused nodes |
| **Hub motors** | Lohner-Porsche (1900), Protean. They remove the transmission, differential and axles. The unsprung-mass penalty is mostly recoverable with damping. They have rarely succeeded in production | Solana's rear hub motors: cheap, light, a little crude |

**Frame types for people's boards** (Wikipedia, *Vehicle frame*; *Space frame*; *Lotus Seven*; *Lugged steel frame construction*; *De Dion tube*):

- **Ladder frame:** two rails joined by cross-members. Simple, tough and good for trucks; poor in torsion; high. Boxed rails (a C-channel closed into a tube) are stiffer than C-section. A tall rail resists bending better than a thick one. → **Harrow Ladder**
- **Backbone:** one strong central tube carries the drivetrain and both suspensions (Lotus Elan, 1962). Its hump intrudes on the cabin, but in an EV the hump can **be** the battery. → **Carrow Keel** (a shipwright's keel)
- **Space frame:** triangulated tubes, so every member is in tension or compression and never bending. High stiffness for the weight; jigs are cheap, so it is ideal for small-batch builders (kit cars, Jaguar C-Type, 300 SL). Its drawback is that it encloses the working volume. → **Solana Lattice**
- **Lugged and brazed tube:** the classic small-workshop bicycle frame. Lower heat preserves the steel's strength, and a broken tube can be "sweated" out and replaced. → Solana's heritage as a cycle works
- **Platform frame:** the floor is part of the frame (VW Beetle, Renault 4, 2CV). It is the ancestor of the skateboard.
- **De Dion tube:** a dead axle with the differential on the frame. Lower unsprung mass than a live axle, constant camber, and simple with leaf springs. → Harrow's rear

**Cottage-scale EV references:**
- Citroën Ami: 485 kg, 5.5 kWh, 6 kW, 45 km/h. Symmetrical parts: the doors and bumpers are the same pressing. No screens; it uses your phone.
- Microlino: 496–530 kg, 6–14 kWh, 12.5 kW, 90 km/h. About 100 staff and 3,700 cars a year in Turin.

These set the scale and the frugality of the three works.

**Cells:** LFP holds 95–172 Wh/kg at cell level (180–205 for newer cells), 227–396 Wh/L, and lasts 2,500–9,000 cycles. It is thermally safe, has no nickel or cobalt, and is made from iron, phosphate, lithium and graphite, all of which the Drops supply. It tolerates imperfect manufacturing. → **people's cells are LFP**, hand-assembled into crates, cartridges and cassettes at roughly 120–130 Wh/kg pack level.

## 2. The Pattern: one body interface for every board

Every board, the Steward's or a works', keeps the **Pattern**:
- **Deck height:** the deck top (the mounting face) is 0.50 m above the ground, laden.
- **Mount rails:** body mounts every **0.75 m** along two mount rails. The rails sit **inboard of the wheels**, as on a skateboard, at a fixed half-spacing for each width class: narrow ±0.50 m, standard ±0.60, broad ±0.70, heavy ±0.80. A body's wheel arches therefore clear the tyres, and **any body fits any board of its class**.
- **Socket:** behind the front axle on the centre line, carrying power and the drive command by wire.

The Standard Pattern Act (VY 398) made this law for people's boards. Each GLB carries the mounts as empties named `mount_<i><L|R>`.

## 3. The Steward's board (pattern HMP-1)

- **Spans:** printed spans 0.75 m long, the same pitch as the Pattern. Each is a lattice of pale Spindle alloy (two waisted side rails at the mount line, a lower chord, struts grown rail to chord and rail to spine, fused nodes) with the **sealed cells** set into it as a smooth pebble with a light seam.
- **Caps:** rounded nose and tail caps with a running light.
- **Pods** at each wheel: an axial-flux motor, reduction, steer-by-wire (±35°), brake-by-wire, active suspension and the pod's own controller in one unit. Two grown arms and a pearl strut carry it from the deck edge out to the wheel. A lens-section fender blade sits over the tyre.
- **Scaling** is by the number of spans and pods. Every wheel is driven and some axles steer:

| board | spans | axles | track | wheel r | pack | power | mass |
|---|---|---|---|---|---|---|---|
| narrow | 5 | 2 | 1.50 m | 0.31 m | 40 kWh | 160 kW | 398 kg |
| broad | 7 | 2 | 1.95 m | 0.40 m | 84 kWh | 360 kW | 780 kg |
| heavy | 10 | 3 | 2.20 m | 0.48 m | 180 kWh | 960 kW | 1,770 kg |

Trams ride on coupled heavy boards; refuse trucks, haulers and farm machines ride on broad and heavy boards. These boards go to the works as the Steward's allotment.

## 4. The three works' boards

| | Harrow Ladder H-27 | Carrow Keel K-28 | Solana Lattice L-25 |
|---|---|---|---|
| **Frame** | two boxed rails (150×75×4 mm rolled and seam-welded steel), 5 cross-members, outriggers to the mount rails | a 340 mm keel tube between the axles, a 60 mm gunwale hoop (it is the mount rail), 4 pairs of ribs, a tube bulkhead at each axle | lugged and brazed chromoly Warren-truss sides (32/25 mm), 7 cross frames, teal lugs |
| **Battery** | 4 steel crates of LFP prismatic cells, 30 kWh | 12 LFP cartridges in the keel, loaded from a bronze hatch at the back, 36 kWh | 4 side-loading cassettes, 24 kWh, swapped in 2 min at a Solana Swap |
| **Motors** | one 60 kW wound-rotor induction motor in the middle → differential → De Dion tube on 7-leaf springs | two 45 kW induction motors on the axle lines, half-shafts with CV boots | two 25 kW outer-rotor ferrite hub motors in the rear wheels |
| **Suspension** | front double wishbones and coil; rear leaf springs; drums | double wishbones and coil-overs all round; front discs | front tube wishbones and coil; rear trailing arms |
| **Electronics** | two Thirty-Twos in a finned steel box | three Thirty-Twos (one per motor and one for the pack), on the keel | two Thirty-Twos, open fins |
| **Mass / L / WB** | 778 kg / 4.25 m / 2.70 m | 692 kg / 4.40 m / 2.80 m | 386 kg / 3.90 m / 2.50 m |
| **Look** | red oxide and black, welds and crates | navy, bronze and polished steel | sun yellow, cream and teal |

People can make these because the Drops supply scrap, ingots and minerals. Induction motors need no rare earths, and ferrite magnets can be made from Drop iron oxide. LFP needs no nickel or cobalt. Tube can be rolled or drawn, welded or brazed, on simple jigs.

## 5. Modules, interchange and destruction

Each board is a list of **modules** in `platforms.json`:
- **Fields:** `id`, `kind`, `pos`, `size` (its collider box), `mass_kg`, `hp`, `attach` (the module it hangs from), plus kind data such as kWh, kW and Nm.
- **In the GLB:** each module is its own object carrying the same data as glTF extras (`module`, `kind`, `mass_kg`, `hp`, `attach`).
- **Wheels** follow the game's rig: `wheel_FL/FR/BL/BR` and `wheel_M1L` …, pivoting at the hub and spinning about X. They are children of their corner or pod.

**The plan for the engine (next):**
- **Assembly:** a vehicle is a board, plus a body of modules (the next step: bodies from the Grok designs), plus the slot fittings (seats, the dash with its gauges, the Wire slot). It is assembled at spawn from module meshes, which is how a vehicle type gets generated on the fly.
- **Destruction:** hits carry the delta-V energy already computed by `ground_vehicle.gd` and deal damage to the modules near the impact. A module at 0 hp detaches and becomes its own rigid body with its own mass. Anything attached to it falls with it.
- **Effects:** losing a pod or a motor drops its power; losing a crate, cartridge or cassette drops pack energy; losing a wheel corner loses that wheel. The board's `mass_kg` is the sum of its modules, so the physics mass changes as parts fly off.

## 6. Sources (fetched 2026-10-01)

- Wikipedia: *General Motors Hy-wire*; *REE Automotive*; *Rivian R1T*; *Giga Press*; *Vehicle frame*; *Space frame*; *Lotus Seven*; *Lugged steel frame construction*; *De Dion tube*; *In-wheel motor*; *Topology optimization*; *Lithium iron phosphate battery*; *Citroën Ami (electric)*; *Microlino*; *Czinger 21C*. The Czinger and Canoo pages had little technical detail.
- **From general knowledge, not checked this session:** Canoo's steer-by-wire skateboard with top hats; Divergent's DAPS printed nodes; BYD's cell-to-body pack; Benteler's BEPS rolling chassis. The session's web-search budget ran out, so these weren't fetched.
