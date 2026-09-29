# Roads research (2026-09-25)

Research behind Space Station Columbia's road standard (SSC_ROAD_STANDARD.md).

- markings.md: centre, edge, lane and stop lines, crosswalks and studs, in the US, Canada, the UK and continental Europe
- signs.md: sign families, shapes, colours, mounting, speed limits
- rail_crossings.md: how level crossings are protected in each region, and how the choice depends on traffic
- cross_sections.md: lane widths, curbs, gutters, shoulders, intersection control and stop lines
- grading.md: maximum grades, vertical curves, cut and fill (AASHTO / TxDOT)

## Where the standard is applied
Regenerate everything after any change to the map or the standard, in this order:
1. `python3 tools/map_expanded.py out.png --game-data` builds the network. It applies §6 of the
   standard through `tools/road_network.py`: joins, creek-free section roads, island links and
   turning circles.
2. `python3 remake/tools/placement.py` places the structures and crossings.
   placement.py also keeps the roads clear (§8): it moves buildings off carriageways and leaves out
   crossings that overlap each other, stand in another road's way or sit on a great bridge's line.
   Then `python3 tools/road_profile.py` grades every road (§7, grading.md). It writes each road's
   height profile and the small bridges' deck heights into `terrain.json`, and removes from
   `placement.json` any crossing that can't lie level within the grade.
   `python3 remake/tools/crossing_profile.py` checks each crossing model's own road surface for steps.
3. `python3 tools/road_furniture.py` writes `godot_project/remake/road_furniture.json`. It sets
   each point's context, the junction and overlap flags, markings, signs, rail crossings and
   signals. Add `--stats` for a junction census.
4. `python3 tools/sign_atlas.py` redraws the sign faces. Only needed when a face changes.
5. `place_aerostats.gd` and `place_ground_vehicles.gd` (headless Godot) place the vehicles.

In the game:
- `MapRoads.gd` draws the road ribbons, markings, curbs and gutters, gravel shoulders and turning
  circles.
- `RoadFurniture.gd` builds the signs, signals and level crossings.

Checks in the running game (DevBridge; see each file's header):
- `remake/tools/road_scan.gd`: every lane's surface, for steps and over-grade stretches.
- `remake/tools/clearance_scan.gd`: a car's body along every lane, against buildings, walks and
  parked cars.
- `remake/tools/drive_test.gd`: a car driven across every bridge, both ways, and down sample
  streets.
- `remake/tools/measure_crossings.gd`: each crossing's deck height where the road meets it.

After any of these, rebake what the game would otherwise build at launch (see research/perf/loading.md):
`godot4 --headless --path . --script res://remake/tools/bake_world.gd -- roads terrain trees walks water`,
then `godot4 --path . --script res://remake/tools/bake_world.gd -- structures` (it needs a display).
