# Vehicle interiors: the driver's station (2026-10-05)

The user: "The guages do not align, the doors leave handles and trim in the openings when they are opened, the
driving position is wrong and the driver's view is often obstructed. Make sure there are windows all around the front
of the vehicle and the drivers has a clear view forward and to the sides. The steering wheel should always be
chest-high when seated. Do extensive research on how car interiors are designed and styled ... The guages need to
work, we need a speedometer and a battery guage."

## How interiors are packaged (research)

- **The H-point and the package dimensions.** Everything is laid out from the driver's H-point (the hip pivot of the
  SAE manikin) and the accelerator heel point: H30 (H-point over the heel), L53 (H-point aft of the heel), H17
  (wheel over the heel), L6 (wheel ahead of the pedal), A40 back angle, W9 wheel diameter. SAE J1100 classes them:
  Class A (cars) H30 127-405 mm, W9 < 450 mm, back angle 5-40 deg; Class B (trucks, buses) H30 405-530 mm,
  W9 450-560 mm, back angle 11-18 deg -- the bus or truck driver sits up, a bigger, flatter wheel before him.
  ([SAE J1100](https://law.resource.org/pub/us/cfr/ibr/005/sae.j1100.2001.html);
  [H-point](https://en.wikipedia.org/wiki/H-point);
  [J1100 summary](https://engineeringcheatsheet.com/sae-j1100-motor-vehicle-dimensions/))
- **Posture.** Drivers prefer a seatback 20-26 deg; a sports car's H30 is 150-250 mm, a truck's over 405 mm; as H30
  falls, the H-point moves aft of the heel (L53 grows). ([Bhise, Ergonomics in the Automotive Design Process](https://vdoc.pub/documents/ergonomics-in-the-automotive-design-process-648sdlcbk5k0);
  [Anthropometric vehicle design](https://link.springer.com/chapter/10.1007/978-3-658-33941-8_7))
- **The eye.** SAE J941's eyellipses (the 95th-percentile spread of drivers' eyes) are the origin of every sight line;
  their centroid sits about 0.63-0.68 m over the H-point at a normal back angle.
  ([SAE J941](https://saemobilus.sae.org/standards/j941_198510-motor-vehicle-drivers-eye-range))
- **The wheel.** 370-400 mm across for cars, larger for trucks and buses; held at 9 and 3; its centre in front of the
  chest so the arms are bent, not reaching. ([steering wheel size guide](https://measurecentre.com/steering-wheel-size-guide-by-vehicle-type/))
- **The instruments.** The cluster is placed by drawing lines from the eyellipse past the wheel's rim to the cluster:
  the gauges must be read through the wheel, not hidden by its rim or spokes; tell-tales must lie above a plane 35 deg
  below the horizontal from the eyes. ([Ford patent, occupant vision zones](https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/6113643);
  [ADR 18 Instrumentation](https://legislation.gov.au/F2006L02738/asmade/2006-08-18/text/original/epub/OEBPS/document_1/document_1.html))
- **The view.** Direct view is what the driver sees without mirrors, from the eyellipse; the A-pillar (everything
  opaque ahead of the driver's eye at the screen's sides, mouldings and door frames included) is kept narrow.
  ([FMVSS 111 notice](https://www.govinfo.gov/content/pkg/FR-2014-04-07/pdf/2014-07469.pdf))
- **Styling (the 1970s the station keeps).** Door panels of padded vinyl over board, clipped on, with an armrest, a
  pull handle, a window crank, chrome trim and woodgrain accents; matching the seats. Dashboards plain, prominent round
  gauges in a bezel or binnacle; plastics, metal and wood veneer in contrasting colours.
  ([Driven to Write: 1970s interiors](https://driventowrite.com/2014/05/26/design-of-car-interiors-1970s/))

## What the fleet does (Builder.station, fleet/builder.py)

- From the driver's H-point (the spec's front seat): the **eye** 0.68 m over it, 0.05 m behind.
- **The wheel**, at the lower chest: car -- centre 0.40 m over the H-point, 0.45 m ahead, 0.38 m across, tilted 25 deg
  from vertical; a driver sitting up (H-point over 0.38 m above the floor: vans, buses, trucks) -- 0.36 over, 0.40 ahead,
  0.46 across, 35 deg. (0.46 / 0.44 first: the rim's top then came within 4 cm of the eye line, across the road.) Three
  spokes (9, 3, 6 o'clock): the top half open. A column down and forward into the dash.
- **The binnacle** 0.72 m (0.80) from the eye, 18 deg (22) below its line -- through the wheel's upper half -- its two dials
  square to the eye: the **speedometer** (0-160 km/h) and the **charge** (E-F, the last fifth red), and the Steward's
  dot-matrix readout between. The dials are live in the game: VehicleBody draws each face and turns its needle
  (`set_gauges(speed, charge)`), fed every tick by the car (its speed) or the craft (its airspeed).
- **The battery**: every vehicle has a charge (0..1; the board's pack, 60 kWh by default); it drains with the power drawn
  (throttle x motor power; a flyer's fans and hover), and flat, it limps (15 % throttle; 30 % thrust).
- **The dash** ends at the wheel (its fascia high enough for the knees), its top under the sight line over it.
- **Doors**: everything a door carries -- the leaf, glass, handle, belt moulding, liveries on it -- moves with it (in
  the game every part on a closer is its own node; handles and trim had been merged into the skin and stayed behind).
- **Glass all round the front**: a fixed quarter window fills any solid side panel between the A-pillar and the first
  door or window (`fill_front_windows`), and flat-fronted cabs get corner glass under the windscreen's sloping edge
  (`corner_glass`): vans, heavy cabs, buses, trains, gondolas, the freighter, the pod, the minivan. The windscreen's
  frit is narrow (6 cm sides, a shallow foot) and the dash's top stays 6.5 deg under the eye to the screen's foot.
- **The view test** (`fleet_test.py --view`) from that eye: 100 deg either side; ahead (+-15 deg, 4 down to 6 up)
  >= 90 % clear, forward (+-60) >= 65 %, each side (60-100 deg, 5 down to 6 up) >= 55 % -- a cab's real pillars and
  frames count, seats don't (the driver looks round a passenger's headrest). 136 of 138 clear (2026-10-05): the
  passenger shuttle's far side (48 %), the pontoon boat's bow fence (88 % ahead).
- **Seats** wear pleated vinyl (`upholstery`: 6 cm pleats, stitched seams, a cross seam, a leather grain), tinted by
  each style's seat colour.
