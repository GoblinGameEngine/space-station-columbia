# Town grading (2026-10-01)

**The problem (the user):** the ground in the towns had become "jagged and uneven", with large trenches in the alleys behind downtown Harrow Falls and elsewhere.

**The cause:** every road was graded to its own profile (AASHTO grades, vertical curves, junction heights), and the ground was cut and filled to meet it at 2:1 out to 14 m. Every building's lot was then levelled to the street height at its front door, blending back over a fixed 4 m. On the bluffs and slopes the result was trenches, embankments and terraced lots.

Measured in Harrow Falls (`MapTerrain.elevation` against the natural ground, 4 m grid):

| | before | after |
|---|---|---|
| ground more than 1 m off the natural ground | 58 % of cells | 4.6 % |
| more than 2 m | 50 % | 2.3 % |
| more than 4 m | 33 % | 0.1 % |
| steeper than 30 % | 30 % | 2.7 % |

## How real towns are graded, and what we do
A town's ground is graded to its streets, as one surface; a street is not cut into the hillside on its own.

`tools/town_grade.py` does the same:
1. Each town's footprint is its lots and its streets, widened by 28 m.
2. The correction each street needs (its graded height minus the natural ground) is held fixed under every carriageway.
3. The correction is spread between the streets by solving Laplace's equation, like a membrane stretched over them.
4. It falls to zero at the footprint's edge (48 m fade) and within 14 m of water, where the banks, water levels and bridge ends were set against the natural ground.

The result is written into the base terrain raster. The ungraded raster is kept as `terrain_base_raw.bin.gz`, and the grading is redone from it each time.

`MapTerrain` then needs only small fixes:
- **Lots** blend back at 1 in 6 on average (the smooth blend peaks at about 1 in 4), out to as far as their height difference needs, up to 18 m.
- **The right of way** (carriageway, tree lawn and sidewalk) is graded flat with the road. Behind a kerb that has a sidewalk, the ground stands at the kerb's top (150 mm), so the sidewalk is walkable.

## Topographic maps
`remake/tools/topo_map.gd` renders the ground the game actually builds:
- hillshade, with contours every 1 m and every 5 m;
- red where grading cuts below the town grade, blue where it fills above it;
- magenta where the ground is steeper than 30 %;
- water in slate blue, roads in grey.

The maps for every town are in `research/roads/topo/`.

**Pipeline order:** `road_profile.py` (as many passes as wanted), then `town_grade.py` last, then `road_furniture.py`. A road_profile pass after town_grade regrades the streets against the graded ground, and they no longer match it: on 2026-10-01 that left 3.8 % of town street points more than 1 m off their ground (Port Carrow 1.9 m down, in a trench). Regrading last brought that to 0 % (mean 0.06 m).
