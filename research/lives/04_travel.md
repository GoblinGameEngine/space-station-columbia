# 4. Travel

Private vehicle ownership is widespread, but some people walk, cycle or take public transit.

## The traits
| trait | values | how |
|---|---|---|
| `car_access` | own_car 80, shared_car 12, none 8 | No car under 16. At 16–17: mostly shared or none. More "none" on low wages, over 84, or in a wheelchair. |
| `commute_mode` | drive 69, carpool 9, transit 3, walk 2.5, bike 0.6, remote 14 | ACS 2023, approximate. Remote work only in desk occupations (clerk, agent, editor, banker, lawyer, librarian). Without a car: transit 45, walk 30, bike 15, carpool 10. Students: school bus, carpool, walk, bike. Preschoolers are driven or walked. University students: transit, bike, walk. Retired people, homemakers and the unemployed don't commute. Farmers and wheelchair users don't walk or cycle to work. |

**Generated** (adult commuters): drive 70.9%, carpool 14.4%, transit 7.8%, walk 3.7%, bike 1.6%,
remote 1.5%. Car access: own 77%, shared 13%, none 10%.

Remote work is far below ACS's 14% because the towns' jobs are mostly hands-on: shops, food,
health, the cannery and the farms. That fits small coastal towns better than the national figure.

## The mode for each trip (NpcLife.mode)
Every trip picks its own mode:
- under **450 m**, everyone walks;
- **work and school trips** use their commute mode: drive, carpool or driven → car; school_bus →
  bus; transit → the tram; bike (under 9 km, else transit); walk (under 2.5 km, else transit);
- **other trips:**
  - a car-owner drives if it's over 900 m (or if they're 70 or older);
  - with a shared car, it's theirs 60% of days;
  - children under 12 go by car with a parent if it's over 1.2 km;
  - otherwise bike (under 7 km, for cyclists), walk (under 1.6 km), or transit;
- **whoever drove or cycled somewhere leaves the same way**: the car is parked outside.

Travel time: street distance (1.3 × straight-line) over the mode's door-to-door speed.

| mode | speed (m/s) | overhead |
|---|---|---|
| walk | 1.3 | — |
| bike | 4.2 | 2 min |
| car | 10 | 4 min parking |
| transit | 5 | 8 min waiting |
| bus | 6 | 5 min |

**Generated** (a week of 800 people's trips): car 46%, walk 44%, transit 7.5%, bus 1.4%, bike 1.2%.
Walking is high because most errands in these small towns are under 450 m.

## The walking network (`tools/places/bake_paths.py`)
The 355 road polylines (streets, main streets, alleys, gravel, county roads and the highway
shoulder) become a graph:
- junctions at shared vertices, at road ends meeting another road (within 4 m, or 25 m for farm
  lanes that stop short), at mid-segment crossings (457 of them), and at the 10 bridges;
- **928 nodes, 1,601 edges, 2 components**; the second is a small group of 19 nodes;
- 1,594 buildings' doors attach to their nearest street within 80 m; 62 lie farther and walk
  straight.

Routes (NpcPlaces.route) run Dijkstra over the graph and walk the **right-hand pavement**: the road
centreline offset by half its width plus 1.2 m. The street route is 1.34 × the straight line. A
route takes about 11 ms and is cached, since the same trips recur daily.

## In the game
- Walkers (and, for now, cyclists) walk their route.
- Drivers and riders appear only for the **door-to-kerb** walk at either end: out of the door to the
  kerb, then gone; or from the kerb to the door, then inside.
- There are no bicycles, cars at kerbs or tram stops yet. Those are **model contracts for later**:
  `bike_rental`, bike racks, `transit_station`, parked cars. Cyclists walking is a placeholder.
