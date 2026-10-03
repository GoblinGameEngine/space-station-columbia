# Vehicle tokens: how a body is tokenised for variation

The user (2026-10-02): "Once they are built, we will begin doing variations for each vehicle so make sure you are
tokenizing the components."

## The grammar

A **token** is one component in the library (`godot_project/remake/vehicles/components/<STD>/<style>.catalog.json` and
`.pack`). Its id is

    <STANDARD>.<role>.<slot>.<side>.<style>.<shape hash>          e.g.  SD180.side_bay.fender.R.carrow_saloon.a1b2c3

and its **interface** is `<STANDARD>/<role>/<slot>/<side>`. Two tokens with the same interface are interchangeable:
they fit the same opening, hinge, mounts and joints of the class's tube frame, whatever their style.

| part of the id | what it is | values |
|---|---|---|
| standard | the class standard it is built to (the frame, the loft, the slots) | SW180, SD180, CU185, FS200, PU190, CP165, LM220, HR220, VN230, HB250 … HX250, BS300 |
| role | what it is: how it is bound, judged in a crash, and tested | side_bay, roof_bay, end_cap, trim, glazing, door_leaf, door_glass, leaf_trim, hatch, hatch_glass, frunk_lid, trunk_lid, reveal, lining_bay, ceiling_bay, end_lining, floor, wheel_well, underpan, frunk_tub, seat, dash, lamp, equipment, cargo_wall, cargo_lining, cargo_floor |
| slot | where on the class it goes | fender, post_0, quarter, rocker_F, roof_0, nose, tail, door_F, window_W1, belt_fender, livery_quarter, head_lamp, tail_lamp, bumper_front, mirror, roof_bar, … |
| side | R, L or C | |
| style | the maker's or variant's look: its own palette, and only the tokens it changes | carrow_saloon, civic_police, … |
| hash | the geometry (to 1 mm): an identical shape is written once | |

## A vehicle is a recipe of tokens

A type's blueprint (`remake/vehicles/fleet/<type>.blueprint.json`) is a list of **placements**:
`[instance id, token id, anchor]`. The instance ids name the slots of this body: `fender_R`, `door_FL`, `pane_W2_L`,
`head_lamps`, `lightbar`. Its **style** names the palette every token is drawn in.

A variant type is built on its class's base type by:

1. **swapping** tokens: the same instance id, a token from the variant's own library (`rebuild`, e.g. black bumpers
   and mouldings for the police car; glass panes for blank panels: `blank_windows` with `reshell`);
2. **adding** tokens: liveries, light bars, signs, racks, booms (`livery`, `inlay`, `equipment`);
3. **repainting**: the variant's palette (`palette`) recolours every token, base ones included. Materials are named
   (paint, paint2, chrome, black, livery1, livery2, lamp_*), and the palette maps each name to a colour.

The base type's other placements are kept as they are.

## What is its own token (never merged into a panel)

- every panel of both shells, every pane, every reveal, every closer and its parts (leaf, glass, handle, belt moulding,
  livery overlay: the `leaf_trim` parts move with their door);
- **dressing:** the head lamps (with the grille band), the grille slots, the tail lamps (with the centre high-mounted
  stop lamp), side markers, identification lamps, front and rear bumpers, each mirror, and each panel's belt
  moulding (`belt_<panel>`) and inlay or livery (`inlay_<panel>`, `livery_<panel>`);
- **equipment:** roof rails, light bar, beacon, taxi sign, roof rack, ladder rack, push bar, spotlight, reefer unit,
  hose bed, fire ladders, aerial ladder, bucket boom, wrecker, brushes, fifth wheel, side arm, awning, cone sign, menu
  board, stop arm, cross-view mirrors, warning lamps, roof hatches, landau bars, bed rack, toolbox, soft-top bows;
- **cabin:** each seat row, the dash with its gauges and wheel;
- **cargo:** the plinth, each side wall and its lining, the rail, the floor, the front wall, the roof and ceiling,
  the rear frame and its closer, each compartment door.

## Making variations (the next step)

- **A palette** is the cheapest variation: a new style with only a palette (no tokens), placed over the base recipe.
  The game can also repaint per vehicle at runtime: `VehicleBody` duplicates a material it changes.
- **Swap a slot** by building a token with the same instance id in a new style library, then writing a blueprint
  whose placement for that instance points at it. `fleet/build.py`'s variant mechanism does this today
  (`rebuild` / `reshell`); `VehicleLibrary.compatible(std, interface)` lists every token that fits a slot.
- **On the fly:** a blueprint is plain data. The game can compose one at run time (pick a token per slot from
  `compatible()`, and a palette) and hand it to `VehicleBody.prepare()`. Each distinct recipe is planned once and
  cached.
