# 12. Industry: the Steward's works, the boards and the vehicle works

Canon from the user (2026-10-01), detailed here. Engineering numbers for the boards are in `tools/vehicles/platforms.py`
(`godot_project/remake/vehicles/chassis/platforms.json`); the chassis models are built from them (`remake/blender/chassis/chassis.py`).

## The Rock

- **what:** the asteroid the station was built inside: a metal-rich rubble body hollowed in the L2 yard (2214-2251) to take the habitat cylinder, which turns inside it on its bearings; the Rock does not turn
- **size:** about 21.4 km across and 24.2 km long; 200-500 m of rock between the cavity and space
- **mining:** the Steward's diggers (tenders' big kin) work its outer face, never the cavity side: cutting, crushing and sorting in vacuum; the spoil is packed back as shield
- **role:** shield: radiation and dust; quarry: the voyage's store of metals, minerals, water and volatiles; mount: the Drive and the Port are set in its stern and bow

## The Spindle

- **what:** the central cylinder on the axis, 200 m across and running cap to cap (22.4 km); it does not turn with the land; its skin carries the Sunline
- **fed_by:** the end-cap hubs: ore and ice come in from the Rock through the bow and stern hubs, along the axis, in near-zero gravity
- **people:** no one has been inside since the Second Lockdown (VY 178); before it, Wardens worked the hub galleries in pressure suits
- **inside:** the great refineries: vacuum smelting, electrolysis, zone refining; foundries and wire-arc printers; powder-bed printers (the boards' lattices); the chip line: one fixed process, the Thirty-Two (see TECH_LIMITS); the panel line (LCD panels, few); cell works: the boards' sealed cells; the tool line: hand tools, bearings, fasteners, motors' laminations

## What the Steward makes for people

| id | what | how often |
|---|---|---|
| raw_materials | raw materials at the Drops (see DROPS) | weekly |
| basic_tools | hand tools, fasteners, bearings, blades, wire, pipe fittings: plain, unbranded, the same design for 500 years | weekly at the Drops |
| boards | the board (pattern HMP-1): an allotment to each of the three vehicle works | a fixed number a year since VY 350 |
| board_pods | replacement corner pods for the boards: leave a worn pod at a Board Drop, a new one is there within the week | on exchange |
| thirty_twos | the Thirty-Two processor boards (see TECH_LIMITS) | monthly, plentiful |
| panels | LCD panels, rationed by the Assembly's Panel Board | a few hundred a year |
| goods_stock | food stock, cloth, medicines, soap, paper: through the Chutes (the Draw) | daily |
| aerostats | aerostats, since the Gift of the Air (VY 405), at the aerodromes | a few a year |

## The Drops

designated places throughout the habitat where the Steward's machines deposit raw materials for people: hatches in the floor that open at night, a fenced yard round each; towns grew works and smelters beside them.

_Placeholder until the Drops are defined in detail (the user, 2026-10-01: 'we will define those Drops later')._

- **scrap:** scrap metal: offcuts, worn parts, mixed steel and aluminium -- the works' main feed
- **alloy:** alloy ingots and billets: steel, aluminium, copper, brass, some nickel and chromium
- **minerals:** deposits of minerals people refine themselves: sulfur, iron ore, copper ore, bauxite, phosphate rock, lithium salts, graphite, silica sand, limestone, salt, clay
- **tools:** the basic-tools line
- **boards:** the Board Drops: the three vehicle works' yards (Harrow Falls, Port Carrow, Solana Point), where the year's boards and exchange pods arrive
- **parts:** the Parts Drops: Thirty-Twos and panels, at the Registry's depots in Kessler and the big towns

- **versus the Chutes:** the Chutes hand out finished goods stock (the Draw); the Drops leave materials to be worked
- **words:** 'a Drop night' (the nights a Drop opens; scrappers wait at the fence); 'drop-grade' (raw, unfinished); 'scrapper' (one who picks a Drop for a living)

## The limits the Steward keeps

### the Thirty-Two

the one processor board the Steward makes for people since the Fourth Lockdown set the Floor (VY 350): a 32-bit chip of early-2000s power (about 400 MHz, 64 MB of memory, a flash store, serial and network ports) on a standard card.

- **supply:** plentiful: tens of thousands a year; they never wear out and are reused for generations
- **used in:** vehicle controllers (motor, pack and brakes); the Wire (radio and the network); the Registry's ledgers; factory machines and lathes; telephones and tills; hospital instruments
- **know-how:** people know how to integrate them -- the College's Book of the Thirty-Two, written from the Wardens' manuals in the Floor's first years and printed for anyone, and the College's courses
- **the cap:** however many are joined, they never add up to a mind: the Steward makes no other kind, the network's links are slow, and every attempt to gang thousands together has failed or been found and stopped (the Lantern, VY 350, was the last that got far)

### Dot-matrix displays

the Steward makes thousands of monochrome LCD dot-matrix panels a year (against a few hundred OLEDs and colour TFTs), from a thumbnail line to a bus's destination sign: black on green or grey, backlit green at night. Common, not free: a population heading for 250,000 and more shares them.

- **uses:** vehicle dashboards (a readout beside the gauges: range, charge, the trip); buses' and trams' destination signs; the Communicator (The System's 240 x 320 screen); shop tills and scales; appliances; clocks; the works' machines

### Panels

OLEDs and high-resolution colour TFTs are the scarce ones: the Steward's panel line makes a few hundred a year; the Assembly's Panel Board rations them.

- **priority:** hospitals and clinics > the Boards (public notice screens) > the Wire's studios and screens > the Registry > schools > aerodromes > works' machines
- **vehicles:** passenger vehicles get none: gauges and a monochrome dot-matrix readout. Some heavy vehicles on Steward boards have the board's own small colour status panel, sealed into the deck

### Gauges

every car and van has electromechanical gauges: speed, pack charge, motor temperature, an ammeter; warning lamps; driven from the controller's Thirty-Two; made by instrument makers, many of them clock and watch families (Fenwick's are the best known).

### The Wire slot

every car has a radio, but it is its own unit: a Wire set slides into a standard opening in the dashboard (the Wire slot) and plugs into a standard socket (power, aerial, speakers, the dimmer line).

- **slot:** 180 x 50 mm, 160 mm deep; the 12-pin Wire plug
- **origin:** the slot is the old Earth single-DIN size, taken from the Wardens' manuals; made the standard by the Wire Slot Accord (VY 452) when the Wire went on the air
- **culture:** sets are bought, swapped, stolen and handed down; a good set outlives three cars; 'pulling your set' when you park in Solana Point

**Why:** the Floor (the Fourth Lockdown, VY 350). The Third Lockdown (VY 271) had already pulled people's goods back to the late 21st century; when people built the Lantern out of exactly those machines, the Steward judged that a further regression would one day be needed unless it set a level people could live on for the rest of the voyage and never threaten the ship from -- and it would rather set it once, gently, than regress again. The College teaches this; Waymakers say it is keeping them humble; most people never think about it -- the Thirty-Two is simply what a computer is

## The boards

**the Pattern (the Steward Pattern):** the board's body interface: the deck top 0.50 m above the ground; body mounts every 0.75 m along both side rails; power and control at the pattern socket behind the front axle. Every board, the Steward's or people's, keeps it: any body fits any board of its width the Standard Pattern Act (VY 398) made it the law for people's boards.

### the Steward board (pattern HMP-1)

- **maker:** steward, since VY 0 (never changed)
- **called:** a true board, a Steward, a pattern board
- **build:** one piece per span: a printed lattice of Spindle alloy, bone-like, the sealed cells set in it; four or more corner pods (motor, steering, brake, suspension and controller in one), bolted on; everything by wire
- **look:** sleek and organic, pale and smooth like bone; very little metal; nothing to see but the deck and the pods
- **sizes:** narrow (1.5 m track), broad (2.0 m track), heavy (2.45 m track, up to 4 axles; trams ride on coupled heavy boards)
- **used for:** trams, refuse trucks, haulers, farm machines, fire and rescue, the Long Calm's pods and vans (old stock)

### the Harrow Ladder

- **maker:** harrow_motor_works, since VY 371
- **called:** a Harrow, a ladder board
- **build:** two boxed rails of rolled-and-welded steel tube with crossmembers; the battery in four steel crates between the rails; one motor in the middle driving the back wheels through a differential and a De Dion tube on leaf springs; drum brakes
- **look:** heavy, square, rivets and welds, red oxide primer and black paint; you can see everything and fix most of it with a welder
- **sizes:** H-24, H-27, H-30 (wheelbase in decimetres)
- **used for:** pickups, farm runabouts, delivery vans, taxis, the family car of the Northland

### the Carrow Keel

- **maker:** carrow_coach_company, since VY 379
- **called:** a Carrow, a keel board, a Coach
- **build:** a ship's keel: a big central tube holding the battery as a string of cartridges, loaded from a hatch at the back; a perimeter hoop (the gunwale) and outrigger ribs; a motor at each axle, inboard, with half-shafts; coil springs and wishbones all round
- **look:** rounded, careful, navy and bronze, the keel tube polished; a shipwright's work
- **sizes:** K-25, K-28, K-31
- **used for:** sedans, coaches (minibuses), the Kessler cab, hearses, the better sort of car

### the Solana Lattice

- **maker:** solana_cycle_and_motor, since VY 384
- **called:** a Solana, a lattice board, a Sunny
- **build:** a bicycle maker's space frame: thin chromoly tubes triangulated and brazed into lugs; the battery as side-loading cassettes you can swap in two minutes; motors in the back wheel hubs; light springs
- **look:** airy, all triangles and bright lugs, sun yellow and cream; light and quick, and it shows a crash
- **sizes:** L-23, L-25
- **used for:** small cars, runabouts, racers, scooters' big cousins, the South Shore's cheap cars

## How things are made

### The Steward

- **mining:** diggers on the Rock's outer face cut, crush and sort ore in vacuum; ice and volatiles are baked out
- **refining:** in the Spindle: vacuum and electric smelting, molten-salt electrolysis for aluminium and titanium, zone refining for silicon; slag back to the Rock
- **printing:** powder-bed fusion for fine parts (the boards' lattices, the pods' housings) and wire-arc deposition for big ones; designs topology-optimised: material only where the loads go, so the parts look grown
- **chips_and_panels:** one fixed chip process (the Thirty-Two) and one small panel line; deliberately never improved
- **cells:** sealed solid cells for the boards; never given out loose
- **delivery:** carts through the Undercroft's galleries to the Drops, the Chutes and the Board Drops, at night

### People

- **remelting:** electric arc and induction furnaces turn Drop scrap into steel and aluminium again; every works and most towns have one
- **rolling_and_tube:** rolling mills make strip and plate (the Falls Rolling Mill at Harrow Falls is the biggest); tube is rolled from strip and seam-welded, or drawn (Solana's chromoly)
- **welding_and_brazing:** arc and gas welding for frames; brazing into lugs for light tube (Solana)
- **casting:** sand casting of aluminium and iron: brackets, hubs, motor housings
- **machining:** lathes and mills, some run by Thirty-Two controllers (the 'smart lathes' of Kessler and Harrow)
- **motors:** induction motors, copper wound by hand and machine in winding shops; ferrite magnets (no rare earths come from the Drops) for small hub motors
- **cells:** LFP cells from Drop iron, phosphate rock, lithium salts and graphite: prismatic cells in steel cans, built into packs, crates and cassettes by hand; heavier than the Steward's and long-lived
- **rubber:** tyres from farmed rubber (Russian dandelion and guayule, grown in the Southland), vulcanised with Drop sulfur, filled with carbon black from the waste kilns
- **glass:** float and pressed glass from Drop silica sand at Port Carrow and Marlowe
- **electronics:** boards built round the Thirty-Two; hand-wound relays and switches; gauge works
- **paint:** lead-free enamels and red oxide primer; colours are a works' signature

## The vehicle works

### Harrow Motor Works (Harrow)

- **seat:** harrow_falls; the Falls Yard (the Wardens' Motor Pool No. 2, the Assembly's from VY 274), on the river below the Falls
- **founded:** VY 354 by Augusta Brenneman
- **board:** harrow_ladder
- **ethos:** build it heavy, build it once; if it breaks, a welder fixes it
- **colours:** red oxide, black
- **buyers:** farmers, tradespeople, the Northland and the Kettle Valley; the Marshals' patrol trucks
- **strong in:** harrow_falls, marlowe, fenwick, dunmore_crossing, cedar_ford, tamarack, countryside
- **Steward allotment:** the largest share of Steward boards (it builds the farm machines and the haulers)
- **reputation:** loved and mocked: 'a Harrow will outlive you, and you'll feel every bump of it'
- **now (VY 500):** about 46% of people's boards; the Ladder little changed in a century; president Della Brenneman-Szabo hired 600 of the Mill No. 2 hands in VY 494

**People:**

- **Augusta Brenneman** (VY 318-397): 'Gus'; forewoman of the Falls Yard; founder of Harrow Motor Works. held the Falls Yard the week the Wardens dissolved: 'the boards keep coming, so we keep building' 'slept on the Drop with a shotgun' (it was a wrench)
- **Elias Thornbury** (VY 341-419): engineer of Old Kettle, the first people-made board. a Ring Line rail fitter; built the first ladder from salvaged rail steel
- **Hiram Okonkwo-Brenneman** (VY 372-451): president of Harrow Motor Works VY 401-445. Gus Brenneman's grandson by marriage; won the Board Wars by outlasting everyone accused of cheering the Keel Recall
- **Della Brenneman-Szabo** (b. VY 448): president of Harrow Motor Works since VY 489. took on 600 of the Mill No. 2 hands in VY 494 wants a new Ladder and the Works' old men won't hear of it

**History:**

- VY 354: the three Yards: the Assembly, its late-21st-century tooling failing under the Floor, lets its three Motor Pools (the Wardens' until VY 274) pass to their workers -- Harrow Motor Works at the Falls Yard, Carrow Coach Company at the Harbour Yard, and (VY 356) Solana Cycle & Motor at the South Yard; the Steward's boards keep arriving at each
- VY 358-361: the Yard Raids: Carrow men and Harrow men steal each other's allotments off the Board Drops at night; two die at the Falls Yard
- VY 362: the Allotment Compact: each works keeps what the Steward leaves in its own yard; the Assembly's Board Office counts the boards
- VY 371: Old Kettle: Elias Thornbury's Harrow Model One, the first board made by people -- a ladder of salvaged rail steel and a crate of hand-made cells; the boards' shortfall begins to close
- VY 390-404: the Board Wars: fourteen years of price cutting, poached welders and sabotage rumours; small makers ruined; three works left standing
- VY 398: the Standard Pattern Act: every board made aboard must keep the Steward's Pattern -- deck height, the mount rails every 0.75 m, the socket -- so any body fits any board
- VY 427: the Keel Recall: cracked steel keels; a Carrow coach breaks in two on the Carrow Pike, eleven dead; every keel called back; Harrow and Solana gain a generation of buyers
- VY 494: Harrow Mill No. 2 closes; Harrow Motor Works takes on 600 of its hands; the Falls Pier opens the same summer

### Carrow Coach Company (Carrow)

- **seat:** port_carrow; the Harbour Yard (the Wardens' Motor Pool No. 1, the Assembly's from VY 274), in the shipyard
- **founded:** VY 354 by Theodora Lindqvist-Vance
- **board:** carrow_keel
- **ethos:** a car is a vessel: build it like a ship, ride like a boat
- **colours:** navy, bronze, cream
- **buyers:** Kessler's lawyers and officials, the North Shore, cab firms, undertakers; the better sort
- **strong in:** port_carrow, kessler, brightwater, haven_point, tern_harbor, bellhaven
- **Steward allotment:** the road trams and coaches: every tram on the roads rides on Carrow-bodied Steward boards
- **reputation:** respected, a little resented: 'Coach money'; the Keel Recall still hurts
- **now (VY 500):** about 31% of people's boards; aluminium keels since VY 431; president Lionel Vance-Okafor

**People:**

- **Theodora Lindqvist-Vance** (VY 315-392): 'the Captain'; shipwright; founder of Carrow Coach Company. 
- **Bartholomew Achebe** (VY 350-431): naval architect; designer of the Carrow Keel. his steel keels cracked forty years on; he lived to see the Recall and never designed again
- **Octavia Fairweather** (VY 405-488): 'the Coach Queen'; president of Carrow Coach Company VY 445-469. Moderator Cordelia Fairweather's cousin sold Steward boards out of the Harbour Yard; resigned VY 469
- **Lionel Vance-Okafor** (b. VY 452): president of Carrow Coach Company since VY 486. the Captain's great-great-grandson; an engineer, not a salesman rebuilding Carrow's name after the Inquiry

**History:**

- VY 354: the three Yards: the Assembly, its late-21st-century tooling failing under the Floor, lets its three Motor Pools (the Wardens' until VY 274) pass to their workers -- Harrow Motor Works at the Falls Yard, Carrow Coach Company at the Harbour Yard, and (VY 356) Solana Cycle & Motor at the South Yard; the Steward's boards keep arriving at each
- VY 358-361: the Yard Raids: Carrow men and Harrow men steal each other's allotments off the Board Drops at night; two die at the Falls Yard
- VY 362: the Allotment Compact: each works keeps what the Steward leaves in its own yard; the Assembly's Board Office counts the boards
- VY 379: the Carrow Keel: Bartholomew Achebe lays a car down like a ship -- the battery in a keel tube, ribs and a gunwale -- and launches it down the slipway at the Harbour Yard
- VY 390-404: the Board Wars: fourteen years of price cutting, poached welders and sabotage rumours; small makers ruined; three works left standing
- VY 398: the Standard Pattern Act: every board made aboard must keep the Steward's Pattern -- deck height, the mount rails every 0.75 m, the socket -- so any body fits any board
- VY 427: the Keel Recall: cracked steel keels; a Carrow coach breaks in two on the Carrow Pike, eleven dead; every keel called back; Harrow and Solana gain a generation of buyers
- VY 469: the Allotment Inquiry: Carrow is found to have sold Steward boards out of the Harbour Yard to private buyers; Octavia Fairweather resigns; the Board Office audits every yard (Moderator Cordelia Fairweather, her cousin, stood aside)

### Solana Cycle & Motor (Solana)

- **seat:** solana_point; the South Yard (the Wardens' Motor Pool No. 3, the Assembly's from VY 274), joined to the Ybarra Cycle Works
- **founded:** VY 356 by Ignacio Ybarra
- **board:** solana_lattice
- **ethos:** light is fast, fast is fun, and you can carry the battery home
- **colours:** sun yellow, cream, teal
- **buyers:** the young, the South Shore, couriers, racers; anyone who wants the cheapest car going
- **strong in:** solana_point, playa_verde, oceanview, pelican_cove, victory_bay
- **Steward allotment:** the smallest share: refuse trucks and the South Shore's farm machines
- **reputation:** the fun one and the fragile one: 'a Solana is a bicycle that got ideas'
- **now (VY 500):** about 23% of people's boards and rising; the Solana Swap's cassette stations in every South Shore town; president Inés Ybarra-Moreno

**People:**

- **Ignacio Ybarra** (VY 322-401): 'Nacho'; bicycle builder; founder of Solana Cycle & Motor. took over the South Yard with his cycle works in VY 356, because nobody else wanted it
- **Pilar Ybarra-Solano** (VY 358-446): designer of the Solana Lattice and the Golondrina; winner of the first Ring Run. won the first Ring Run at 54, in a car she designed at 26
- **Rafael Quintero** (b. VY 461): 'Rafa'; Solana's racing driver; seven-time Ring Run winner. won the Ring Run in VY 487, 489, 491, 493, 495, 496 and 498 Port Carrow boos him
- **Luis Arrieta-Wu** (b. VY 438): 'Lucky Luis', developer of Pier Plaza and Pacific City. a Tern Exodus boy made good four children by three marriages, two from gifted shares
- **Inés Ybarra-Moreno** (b. VY 457): president of Solana Cycle & Motor since VY 491. Nacho Ybarra's great-granddaughter means to sell a Solana in Harrow Falls

**History:**

- VY 354: the three Yards: the Assembly, its late-21st-century tooling failing under the Floor, lets its three Motor Pools (the Wardens' until VY 274) pass to their workers -- Harrow Motor Works at the Falls Yard, Carrow Coach Company at the Harbour Yard, and (VY 356) Solana Cycle & Motor at the South Yard; the Steward's boards keep arriving at each
- VY 384: the Golondrina: Pilar Ybarra-Solano's first car, a bicycle-maker's lattice of brazed chromoly, half the weight of a Harrow
- VY 390-404: the Board Wars: fourteen years of price cutting, poached welders and sabotage rumours; small makers ruined; three works left standing
- VY 398: the Standard Pattern Act: every board made aboard must keep the Steward's Pattern -- deck height, the mount rails every 0.75 m, the socket -- so any body fits any board
- VY 412: the first Ring Run: a road race once round the world; Pilar Ybarra-Solano wins in a Golondrina, in 9 hours 41 minutes
- VY 452: the Wire Slot Accord: the three works agree one opening and one plug for car radios, so a Wire set fits any car; Leopold Varga-Hayes puts the first sets on sale
- VY 474: the Solana Swap: battery cassette stations in every South Shore town, paid for by Lucky Arrieta-Wu: drive in flat, drive out full in two minutes

## Rivalries

- harrow_motor_works / carrow_coach_company (-0.5): the old feud: work truck against carriage, Kettle Valley against North Shore; the Keel Recall (VY 427), which Harrow's men were accused of gloating over
- carrow_coach_company / solana_cycle_and_motor (-0.6): the Port Carrow - Solana Point rivalry of the Spin Cup carried onto the road; the Ring Run
- harrow_motor_works / solana_cycle_and_motor (-0.2): mostly contempt both ways ('bicycles' / 'tractors'), and an alliance against Carrow in the Allotment Inquiry
