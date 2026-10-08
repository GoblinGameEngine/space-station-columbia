extends RefCounted

## Where each bridge meets its road, at both ends: how far the road's centreline is from the bridge's
## middle there (m), the angle between them (degrees), and the step from the road's surface to the
## deck (m).  Great bridges (GreatBridges.spans: the ends of their lines) and small crossings (the
## ends of each model's deck and of its approach slabs).  From DevBridge:
##   return load("res://remake/tools/bridge_ends.gd").check(root.get_tree())
## A row is flagged past LAT m, ANG degrees or STEP_H m.

const LAT := 0.5
const ANG := 3.0
const STEP_H := 0.05


static func check(tree: SceneTree) -> Dictionary:
	MapTerrain.elevation(0.0, 0.0)
	var rows := []
	var gb := tree.current_scene.get_node("GreatBridges")
	for sp in gb.spans:
		if sp.rail:
			continue
		var line: PackedVector2Array = sp.line
		var n := line.size()
		for end in [[line[0], (line[0] - line[1]).normalized()], [line[n - 1], (line[n - 1] - line[n - 2]).normalized()]]:
			var p: Vector2 = end[0]
			var out: Vector2 = end[1]                   # pointing off the bridge, onto the road
			var r := _road_at(p + out * 1.0)
			var deck := _deck_top(tree, p - out * 0.2)
			var road_h := MapTerrain.elevation(fposmod((p + out * 0.2).x, StationGeo.CIRC), (p + out * 0.2).y) + MapRoads.LIFT
			rows.append(_row(sp.id, r, p, out, deck - road_h))
	var pl: Array = JSON.parse_string(FileAccess.get_file_as_string("res://remake/placement.json")).structures
	for e in pl:
		if e.kind != "crossing" or not e.has("deck"):
			continue
		var c := cos(float(e.yaw))
		var sn := sin(float(e.yaw))
		var lx: float = (e.fmin[0] + e.fmax[0]) * 0.5
		var deck := MapTerrain.pad_height(e.id)
		for sg: float in [-1.0, 1.0]:
			var lz: float = sg * float(e.deck[0]) * 0.5
			var p := Vector2(float(e.s) + lx * sn - lz * c, float(e.x) + lx * c + lz * sn)
			var out := Vector2(-c, sn) * sg                   # local +z in (s, x), off the deck
			var r := _road_at(p + out * 1.0, str(e.id).begins_with("RAIL-"))
			var q := p + out * 0.2
			var road_h := MapTerrain.elevation(fposmod(q.x, StationGeo.CIRC), q.y)     # (the road is graded level with the deck here)
			rows.append(_row(e.id, r, p, out, deck - road_h))
	var bad := rows.filter(func(w): return w.flag)
	return {"ends": rows.size(), "flagged": bad.size(), "rows": bad}


static func _row(id: String, r: Array, p: Vector2, out: Vector2, dh: float) -> Dictionary:
	if r.is_empty():
		return {"id": id, "at": p, "flag": true, "why": "no road"}
	var tang: Vector2 = r[1]
	var ang := rad_to_deg(acos(clampf(absf(tang.dot(out)), 0.0, 1.0)))
	var lat: float = r[0]
	return {"id": id, "at": p, "lat": snappedf(lat, 0.01), "ang": snappedf(ang, 0.1), "dh": snappedf(dh, 0.01),
		"flag": lat > LAT or ang > ANG or absf(dh) > STEP_H}


static func _road_at(p: Vector2, rail := false) -> Array:
	## [distance from p to the nearest road's centreline, that road's unit tangent there] (within 15 m)
	var best := 15.0
	var tang := Vector2.ZERO
	var s := fposmod(p.x, StationGeo.CIRC)
	for it in MapTerrain._items(Vector2i(floori(s / MapTerrain.CELL), floori(p.y / MapTerrain.CELL))):
		if it[0] != "road":
			continue
		var rd: Dictionary = MapTerrain._d.roads[it[1]]
		if (rd.cls == "rail") != rail:
			continue
		for k in range(it[2], it[3]):                  # (an entry is a run of segments: MapTerrain.ROAD_RUN)
			var a: Vector2 = rd.pts[k]
			var b: Vector2 = rd.pts[k + 1]
			var pr := MapTerrain._seg_proj(s, p.y, a[0], a[1], b[0], b[1])
			if pr.x < best:
				best = pr.x
				tang = Vector2(StationGeo.wrap_ds(b[0] - a[0]), b[1] - a[1]).normalized()
	return [] if tang == Vector2.ZERO else [best, tang]


static func _deck_top(tree: SceneTree, p: Vector2) -> float:
	## the great bridge's deck surface under p (a ray down onto its collision)
	var s := fposmod(p.x, StationGeo.CIRC)
	var up := StationGeo.up(s)
	var top := StationGeo.point(s, p.y, MapTerrain.elevation(s, p.y) + 30.0)
	var space: PhysicsDirectSpaceState3D = (tree.current_scene as Node3D).get_world_3d().direct_space_state
	var ex: Array[RID] = []
	for attempt in 6:
		var q := PhysicsRayQueryParameters3D.create(top, top - up * 40.0, 1)
		q.exclude = ex
		var h: Dictionary = space.intersect_ray(q)
		if h.is_empty():
			return NAN
		if str((h.collider as Node).get_path()).contains("GreatBridges"):
			return StationGeo.h_of(h.position)
		ex.append(h.rid)
	return NAN
