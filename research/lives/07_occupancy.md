# 07 Occupancy: every building, every room, its people

The user, 2026-10-07: "every single building needs a purpose, every house needs residents, every shop needs workers and
every store needs shoppers ... assigning characters to each and every building, and each and every room of every
building with characters being assigned to multiple rooms of multiple buildings ... generate it on the fly while
in-game. The story engine will have to work with that."

This is the contract between the world (buildings, people, places) and the story engine (the deck-ea session:
journal, event log, casting, arcs, quests). It was agreed between the two sessions on 2026-10-07.

## The pipeline

| Step | Tool | Output |
|---|---|---|
| Build a building | `remake/blender/build_record.py` (every generator goes through `gbhouse.House`) | the glb and the **raw plan** `remake/rooms/raw/<id>.json`: rooms, doors, stairs, storeys, every piece of furniture placed in each room, and the **audit** |
| Audit it | `remake/blender/gbaudit.py`, which runs in every build | **sealed**: rays from inside every room meet the building before they leave it. **No clipping**: no furniture or partition vertex is past an exterior wall's inner face or above the roof. **Doors**: every leaf is solid or glass across its whole face, with closed solids and no holes. The build prints `AUDIT <id> ok|FAIL` |
| Give it meaning | `tools/rooms/make_rooms.py` | `godot_project/remake/rooms/<Settlement>.json`: rooms, units, doors with locks, containers, delivery points, rostered posts |
| Place units | `tools/places/bake_places.py` | manifest buildings' business units, with type and jobs from their posts, as `<building>/<unit>` |
| People | `NpcOccupancy` (`remake/characters/npc_occupancy.gd`) | households per dwelling unit, a bed each, posts filled from the settlement's own people, seeded vacancies |
| Cache | `remake/tools/bake_lives.gd` | `npc_lives.json`. For manifest towns this is exactly NpcOccupancy's answer, so it is a cache and not an authority |

## The manifest (per building)

- `purpose`: `["dwelling"]` and/or the place types of its businesses. No building is without one. Vacant storefronts
  were removed from the town generator.
- `rooms[rid]`:
  - `use`: one of bedroom, living, kitchen, bath, hall, sales, stockroom, office, ward, nurse_station, classroom, nave,
    lobby, guest_room, work_floor, and so on.
  - `floor`.
  - `z` = [floor height, ceiling height].
  - `rect` = [x0, z0, x1, z1] in the glb frame (x right, z back).
  - `unit`.
  - `access`: private, common, public or staff.
  - `beds`: [[x, y, z, yaw]].
  - `seats`.
  - `containers`: [{cid, type, at, owner}]. The types are dresser, wardrobe, desk, safe, file_cabinet, register,
    display_case, fridge, cabinets, shelves, and so on. The owner rules are:
    - `occupant`: whoever sleeps in that room;
    - `household`;
    - `post`: the holder of the post working there;
    - `role:manager`;
    - `business`;
    - `public`;
    - `building`.
  - `stations`: tills, desks, counters and the like, where a post stands.
- `doors`: [{node, rooms [a, b | "outside"], ext, floor, at, lock}].
  - `node` is the glb's `door_<name>` prefix.
  - `lock` is one of these rules:
    - `residents`: the unit's people hold keys;
    - `privacy`: a bath, which locks from inside;
    - `hours`: a business's public door, open in its hours and locked otherwise, with staff holding keys;
    - `staff`: staff only, which is trespass for others;
    - `manager`: the office with the safe;
    - `open`.
- `units[uid]`:
  - `dwelling`: `households` and `bedrooms`.
  - `business`: `place` (an `npc_places.json` type) and `posts`.
  - `common`: shared halls, stairs and garages.
  - Every unit has a `delivery`: {door, to}, where `to` is `resident` or `on_duty:<role>`. This is the Courier's
    handoff point.

## Posts and shifts

- Templates come from the place's hours:
  - up to 10 h: one shift;
  - up to 16 h: early and late;
  - 24 h: 07–15, 15–23 and 23–07.
- A headcount is spread over the shifts by weight (day 0.45, late 0.33, night 0.22). Managers work days.
- Places open six or seven days a week run a weekly **rota**: every post has two days off in a row, spread across
  its shift.
- **Relief posts** are added wherever a shift on some open day would otherwise have no one at the front.
- A **night shift belongs to the day it starts**. `on_duty` at 02:00 also checks the previous day's night posts.
- Post ids are `<building>/<unit>:<role>:<n>`, so the event log can say "the night nurse on Ward 2" whoever fills
  the post.

## People (NpcOccupancy)

- **One settlement is one labour market**, solved from the world seed alone and independent of what else is loaded.
- Posts are filled in a hashed order. Each post goes to the nearest free person of its trade within a hashed sample
  of 16. If there is none, it goes to a working-age adult who is unemployed, a homemaker, or in a trade with no post in
  town; that person takes the job, and `occupation_was` keeps what they were before.
- A few posts stand **vacant** in the baseline, at a seeded rate set by the town's economy (2% for a stable town, up
  to 6% for the rust belt). Each carries a `vacant_reason`: unfilled, chute_shortage, just_quit, budget_cut or
  on_leave. Understaffing is a quest need.
- People who are left over are `jobless`, and look for work.
- In the bed rules, the couple takes the biggest bedroom, then the eldest take one room each, and when rooms run out
  people share the least crowded one.
- **Stability**: the baseline depends on the seed only. The story's journal overrides only the person a delta names.
  A firing leaves the post open, and the market is never re-solved.

## Queries

All of these are pure and work for unloaded settlements:

```
NpcOccupancy.on_duty(seed, "C-077/B0" | "C-077#R1F0_0", day, hour) -> [{post, pid, role, room, vacant}]
NpcOccupancy.roster(seed, uid)       NpcOccupancy.residents(seed, building[, unit])
NpcOccupancy.rooms_of(seed, pid)     NpcOccupancy.who(seed, place, day, hour)     NpcOccupancy.where(seed, pid, day, hour)
```

## Ids

- `pid "<building>:<n>"` is an **immutable origin id**. Once someone moves, their home comes from the journal.
- People born by deltas are `n:<seq>`.
- An indoor place is `<building>#<rid>`.
- A unit is `<building>/<unit>`.
- For alpha, saves carry a world-version stamp. Later, ids must stay stable across regenerations.

## Who owns what

| Side | Owns |
|---|---|
| World side (this repo's `remake/characters`, `tools/rooms`, generators) | manifests, purposes, beds, posts, the market, the query API |
| Story engine (deck-ea) | the journal and delta schema, the event log, met people and affinity, casting on top of `candidates()`, arcs and quests (under `remake/story/`) |
