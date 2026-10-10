#!/bin/bash
# regen_world.sh [FROM_STEP] -- the whole regeneration after a map change (research/roads/SSC_ROAD_STANDARD.md "Pipeline",
# research/perf/loading.md "Rerun the bakes"), each step logged; stops at the first failure.
cd ~/goblin-engine
P=~/.venvs/ssc-assets/bin/python
GD=$(realpath godot/godot4)
L=reference/tmp/regen_logs
mkdir -p $L
FROM=${1:-1}
n=0
step() {
  n=$((n + 1))
  [ $n -lt $FROM ] && return 0
  local name=$1; shift
  echo "=== $n $name  $(date +%H:%M:%S)"
  if ! "$@" > $L/$(printf %02d $n)_$name.log 2>&1; then
    echo "FAILED at step $n ($name) -- see $L/$(printf %02d $n)_$name.log"; tail -15 $L/$(printf %02d $n)_$name.log; exit 1
  fi
  tail -2 $L/$(printf %02d $n)_$name.log
}
gd() { (cd godot_project && "$GD" "$@"); }
step import          gd --headless --path . --import
step road_fix        $P tools/road_fix.py        # (every road's line drivable: de-staired, rounded, joined, straight over its bridges)
step street_rules    $P tools/street_rules.py
step placement       $P remake/tools/placement.py
step road_fix2       $P tools/road_fix.py --after-placement   # (the kinks the crossings' snapping leaves, rounded)
step road_profile1   $P tools/road_profile.py
step road_profile2   $P tools/road_profile.py
step town_grade      $P tools/town_grade.py
step make_rooms      $P tools/rooms/make_rooms.py
step make_places     $P tools/places/make_places.py
step bake_places     $P tools/places/bake_places.py
step bake_paths      $P tools/places/bake_paths.py
step bake_lives      gd --headless --path . --script res://remake/tools/bake_lives.gd
step make_vehicles   $P tools/places/make_vehicles.py
step bake_transit    gd --headless --path . --script res://remake/tools/bake_transit.gd
step street_rules2   $P tools/street_rules.py
step street_names    $P tools/street_names.py
step parking_lots    $P tools/parking_lots.py
step road_furniture  $P tools/road_furniture.py
step place_aerostats gd --headless --path . --script res://remake/tools/place_aerostats.gd
step place_ground    gd --headless --path . --script res://remake/tools/place_ground_vehicles.gd
# (one process each: all five in one ran past the Deck's 14 GB on the 1:1 map and earlyoom killed it, 2026-10-08)
step bake_pads       gd --headless --path . --script res://remake/tools/bake_world.gd -- pads
step bake_roads      gd --headless --path . --script res://remake/tools/bake_world.gd -- roads
step bake_terrain    gd --headless --path . --script res://remake/tools/bake_world.gd -- terrain
step bake_trees      gd --headless --path . --script res://remake/tools/bake_world.gd -- trees
step bake_walks      gd --headless --path . --script res://remake/tools/bake_world.gd -- walks
step bake_water      gd --headless --path . --script res://remake/tools/bake_world.gd -- water
step bake_structures gd --path . --script res://remake/tools/bake_world.gd -- structures
step pda_political   $P tools/pda_political_map.py
step pda_detail      $P tools/pda_detail_map.py
echo "=== done $(date +%H:%M:%S)"
