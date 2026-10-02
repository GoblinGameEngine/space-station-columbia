extends RefCounted
class_name TubeFrame

## A vehicle's welded tube space frame (research/vehicles/MODULAR_VEHICLES.md): the structure between the
## skateboard platform (the Steward board, which it is bolted to) and the body panels, inside and out,
## which are fastened to it. Built from the class standard (remake/vehicles/standards/<id>.json): a ring of
## joints at every slot boundary along the body, tubes round each ring, stringers between rings, and
## diagonal braces in the roof, the floor and the lower side panels (the window band and the door
## apertures are open).
##
## Damage bends it: impact() pushes the joints near a blow in, then the tubes pull their neighbours along
## (a few relaxation passes) and take a permanent set where they were strained past yield. The skin is
## bound to the joints (bind(): each point to the four joints round it), so the panels dent with the frame;
## a panel whose mounts are strained past its tolerance (strain()) comes off.

var nodes_rest := PackedVector3Array()
var nodes := PackedVector3Array()        # where the joints are now
var inv_mass := PackedFloat32Array()     # 0 for none; the bolted joints are held by the board
var beams: Array = []                    # [a, b, rest length, diameter]
var stations := PackedFloat32Array()     # ring z (Godot, front -> back)
var ring_n := 0
var names: Array = []                    # joint names round a ring
var profile: Array = []                  # [Vector2(x, y)] of each ring
var bind_segs: Array = []                # [a, b] profile segments points are bound to
var std: Dictionary
var centres: Array = []                  # each ring's middle (Vector2): points are bound by their angle round it
var orders: Array = []                   # each ring's joints sorted by that angle: [[joint, angle]]


static func build(p_std: Dictionary, bp: Dictionary, openings: Dictionary) -> TubeFrame:
	## openings: {"R": [[z0, z1, "door"|"window"]], "L": [...]} -- where the side is open.
	var f := TubeFrame.new()
	f.std = p_std
	var ring: Array = p_std.ring
	f.ring_n = ring.size()
	for r in ring:
		f.names.append(str(r[0]))
	# (no hoops in a nose or tail: a cap is a moulding bolted to the last full hoop, and bends with it)
	# the rings: the standard's own, one shape per station (a car: the nose, the hood, the screen, the cabin), or
	# the one ring at every blueprint station (a tram section: the same section all along)
	var zs: Array = []
	var shapes: Array = []
	if p_std.has("rings"):
		var rl: Array = (p_std.rings as Array).duplicate()
		rl.sort_custom(func(a, b): return float(a.y) > float(b.y))         # (front first: Godot z ascending)
		for r in rl:
			zs.append(-float(r.y))
			shapes.append(r.joints)
	else:
		for z in bp.stations:
			zs.append(float(z))
			shapes.append(ring)
	# the open tops (no member across the windscreen or a lid): Godot z ranges
	for t in p_std.get("top_openings", []):
		if not openings.has("T"):
			openings["T"] = []
		openings["T"].append([-float(t[1]), -float(t[0]), str(t[2])])
	# the wheel arches are openings low in the sides: no rail or post may cross one (it would show)
	for ax in p_std.axles:
		for sd in ["R", "L"]:
			if not openings.has(sd):
				openings[sd] = []
			openings[sd].append([-float(ax) - float(p_std.arch_half), -float(ax) + float(p_std.arch_half), "arch"])
	var bolted: Array = p_std.bolted
	for ri in zs.size():
		var z: float = zs[ri]
		f.stations.append(z)
		var prof: Array = []
		var shape: Array = shapes[ri]
		for r in shape:
			var x := float(r[1])
			var y := float(r[2])
			prof.append(Vector2(x, y))
			var zz := z
			if ri == 0 or ri == zs.size() - 1:                 # (the end hoops stand inside the end cavity)
				zz += float(p_std.get("end_inset", 0.0)) * (1.0 if ri == 0 else -1.0)
			var nm0 := str(r[0])
			var low_cant := nm0.begins_with("cant") and y < float(p_std.door.head)        # (a car's A-pillar: by the door)
			if (nm0.begins_with("belt") or nm0.begins_with("head") or low_cant) and nm0.length() > 5:
				zz += f._jamb_step(openings, nm0.substr(nm0.length() - 1), z)
			f.nodes_rest.append(Vector3(x, y, zz))
			f.inv_mass.append(0.15 if bolted.has(str(r[0])) else 1.0)
		f.profile.append(prof)
		f._ring_binding(prof)
	f.nodes = f.nodes_rest.duplicate()
	var idx := func(name: String) -> int: return f.names.find(name)
	var main_d := float(p_std.tubes.main_d)
	var brace_d := float(p_std.tubes.brace_d)
	# the binding segments (and the ring tubes): up the right side, over the roof, down the left; the floor
	var chain := ["skirt_R", "sill_R", "belt_R", "head_R", "cant_R", "roof_R", "crown", "roof_L", "cant_L", "head_L", "belt_L", "sill_L", "skirt_L"]
	for i in chain.size() - 1:
		f.bind_segs.append([idx.call(chain[i]), idx.call(chain[i + 1])])
	f.bind_segs.append([idx.call("sill_L"), idx.call("floor_C")])
	f.bind_segs.append([idx.call("floor_C"), idx.call("sill_R")])
	var n := f.ring_n
	for ri in zs.size():
		var z: float = zs[ri]
		for sg in f.bind_segs:
			var na := str(f.names[sg[0]])
			var nb := str(f.names[sg[1]])
			var side := "R" if na.ends_with("_R") or nb.ends_with("_R") else ("L" if na.ends_with("_L") or nb.ends_with("_L") else "C")
			var pair := [na.substr(0, na.find("_")) if na.find("_") > 0 else na, nb.substr(0, nb.find("_")) if nb.find("_") > 0 else nb]
			var post: bool = pair.has("sill") and pair.has("belt")
			var band: bool = pair.has("belt") and pair.has("head")
			var above: bool = pair.has("head") and pair.has("cant")
			if side != "C" and (post or band or above) and f._open_at(openings, side, z, "door"):
				continue                                 # (a door aperture: no post across it)
			if side != "C" and band and f._open_at(openings, side, z, "window"):
				continue                                 # (a window: no post across it)
			if side != "C" and (pair.has("skirt") or pair.has("sill")) and f._open_at(openings, side, z, "arch"):
				continue                                 # (a wheel arch: nothing low across it)
			if TOP.has(pair[0]) and TOP.has(pair[1]) and f._top_open(openings, z):
				continue                                 # (the windscreen, a lid: nothing across the top)
			f._beam(ri * n + int(sg[0]), ri * n + int(sg[1]), main_d)
		if ri == 0:
			continue
		var z0: float = zs[ri - 1]
		var zm := (z0 + z) * 0.5
		for j in n:
			var nm := str(f.names[j])
			if (nm.begins_with("belt") or nm.begins_with("head")) and f._open_at(openings, nm.substr(5), zm, "door"):
				continue                                 # (the belt and head rails stop at a door)
			if (nm.begins_with("skirt") or nm.begins_with("sill")) and nm.length() > 5 and f._touches(openings, nm.substr(nm.length() - 1), z0, z, "arch"):
				continue                                 # (and the skirt and sill rails at a wheel arch)
			if (nm.begins_with("roof") or nm == "crown") and f._top_touches(openings, z0, z):
				continue                                 # (and the roof rails over a windscreen or a lid)
			f._beam((ri - 1) * n + j, ri * n + j, main_d)
		# the braces: the roof, the floor, the lower side panels where there's no door
		if not f._top_touches(openings, z0, z):
			f._beam((ri - 1) * n + idx.call("roof_R"), ri * n + idx.call("crown"), brace_d)
			f._beam((ri - 1) * n + idx.call("crown"), ri * n + idx.call("roof_L"), brace_d)
		f._beam((ri - 1) * n + idx.call("sill_R"), ri * n + idx.call("floor_C"), brace_d)
		f._beam((ri - 1) * n + idx.call("floor_C"), ri * n + idx.call("sill_L"), brace_d)
		for sd in ["R", "L"]:
			if not f._open_at(openings, sd, zm, "door") and not f._touches(openings, sd, z0, z, "arch"):
				f._beam((ri - 1) * n + idx.call("sill_" + sd), ri * n + idx.call("belt_" + sd), brace_d)
		for sd in ["R", "L"]:                            # (the floor braces' sill ends, clear of an arch)
			if f._touches(openings, sd, z0, z, "arch"):
				f._unbeam((ri - 1) * n + idx.call("sill_" + sd), ri * n + idx.call("floor_C"))
				f._unbeam((ri - 1) * n + idx.call("floor_C"), ri * n + idx.call("sill_" + sd))
	return f


const TOP := ["cant", "roof", "crown"]


func _top_open(openings: Dictionary, z: float) -> bool:
	for o in openings.get("T", []):
		if z > float(o[0]) + 0.02 and z < float(o[1]) - 0.02:
			return true
	return false


func _top_touches(openings: Dictionary, z0: float, z1: float) -> bool:
	for o in openings.get("T", []):
		if minf(z0, z1) < float(o[1]) - 0.02 and maxf(z0, z1) > float(o[0]) + 0.02:
			return true
	return false


func _jamb_step(openings: Dictionary, side: String, z: float) -> float:
	## A ring at a door's edge: its side posts stand back from the jamb (the tube clear of the aperture).
	for o in openings.get(side, []):
		if str(o[2]) != "door":
			continue
		if absf(z - float(o[0])) < 0.03:
			return -0.035                                # (before the aperture: step back)
		if absf(z - float(o[1])) < 0.03:
			return 0.035
	return 0.0


func _touches(openings: Dictionary, side: String, z0: float, z1: float, kind: String) -> bool:
	## Does the span z0..z1 reach into an opening of this kind?
	for o in openings.get(side, []):
		if str(o[2]) == kind and minf(z0, z1) < float(o[1]) + 0.02 and maxf(z0, z1) > float(o[0]) - 0.02:
			return true
	return false


func _unbeam(a: int, b: int) -> void:
	for i in range(beams.size() - 1, -1, -1):
		if (beams[i][0] == a and beams[i][1] == b) or (beams[i][0] == b and beams[i][1] == a):
			beams.remove_at(i)


func _open_at(openings: Dictionary, side: String, z: float, kind: String) -> bool:
	## Is z in an opening of this kind? (A window counts out to the tube's radius and a margin past its
	## edge: a post at the glass's edge would show through it.)
	var m := -0.03 if kind == "window" or kind == "arch" else 0.02
	for o in openings.get(side, []):
		if str(o[2]) == kind and z > float(o[0]) + m and z < float(o[1]) - m:
			return true
	return false


func _beam(a: int, b: int, d: float) -> void:
	if a < 0 or b < 0 or a == b or nodes_rest[a].distance_to(nodes_rest[b]) < 0.02:
		return
	beams.append([a, b, nodes_rest[a].distance_to(nodes_rest[b]), d])


# -- binding the skin --------------------------------------------------------------------------------------

func _ring_binding(prof: Array) -> void:
	## A ring's middle (half way up its middle line) and its joints in order round it.
	var lo := INF
	var hi := -INF
	for q in prof:
		lo = minf(lo, (q as Vector2).y)
		hi = maxf(hi, (q as Vector2).y)
	var c := Vector2(0.0, (lo + hi) * 0.5)
	centres.append(c)
	var order: Array = []
	for i in prof.size():
		order.append([i, fposmod(atan2((prof[i] as Vector2).y - c.y, (prof[i] as Vector2).x - c.x), TAU)])
	order.sort_custom(func(a, b): return a[1] < b[1])
	orders.append(order)


func bind(p: Vector3) -> Array:
	## [4 joint indices, 4 weights]: p's place between the two rings either side of it (t) and between the
	## two joints either side of it round the ring, by angle about the ring's middle (u) -- bilinear. The
	## weights vary continuously with position (no nearest-member switch), so two panels that touch move
	## together under any bending: seams never open (the user's rule: no gaps between panels, ever).
	var nr := stations.size()
	var k := 0
	while k < nr - 2 and p.z > stations[k + 1]:
		k += 1
	var z0 := stations[k]
	var z1 := stations[mini(k + 1, nr - 1)]
	var t := clampf((p.z - z0) / (z1 - z0), 0.0, 1.0) if z1 > z0 else 0.0
	var n := ring_n
	var k1 := mini(k + 1, nr - 1)
	var A := _round(k, Vector2(p.x, p.y))
	var B := _round(k1, Vector2(p.x, p.y))
	return [[k * n + A[0], k * n + A[1], k1 * n + B[0], k1 * n + B[1]], [(1 - t) * (1 - A[2]), (1 - t) * A[2], t * (1 - B[2]), t * B[2]]]


func _round(k: int, q: Vector2) -> Array:
	## [joint a, joint b, u]: q's place between the two joints of ring k either side of it, by angle round the
	## ring's middle (each ring its own: a car's rings differ along it; continuous in q).
	var order: Array = orders[k]
	var ang := fposmod(atan2(q.y - (centres[k] as Vector2).y, q.x - (centres[k] as Vector2).x), TAU)
	var m := order.size()
	for i in m:
		var a0: float = order[i][1]
		var a1: float = order[(i + 1) % m][1]
		var span := fposmod(a1 - a0, TAU)
		var off := fposmod(ang - a0, TAU)
		if off <= span:
			return [int(order[i][0]), int(order[(i + 1) % m][0]), off / span if span > 1e-6 else 0.0]
	return [int(order[0][0]), int(order[0][0]), 0.0]


func displacement(bound: Array) -> Vector3:
	## How far a bound point has moved (the joints' moves only).
	var out := Vector3.ZERO
	var ids: Array = bound[0]
	var ws: Array = bound[1]
	for i in 4:
		out += (nodes[ids[i]] - nodes_rest[ids[i]]) * float(ws[i])
	return out


func deformed(v: Vector3, bound: Array) -> Vector3:
	## Where a bound point (as built) is now: each of its joints carries it, moved and turned -- exactly
	## as the skinned mesh draws it.
	var out := Vector3.ZERO
	var ids: Array = bound[0]
	var ws: Array = bound[1]
	for i in 4:
		var j: int = ids[i]
		var q: Quaternion = rot[j] if j < rot.size() else Quaternion.IDENTITY
		out += (nodes[j] + q * (v - nodes_rest[j])) * float(ws[i])
	return out


var rot: Array = []                       # each joint's turn (Quaternion), from how its tubes turned
var _adj: Array = []                      # joint -> [joints it is tubed to]


func update_turns() -> void:
	## Each joint's best turn: the average of the arcs its tubes swung through (so the skin's normals turn
	## with a dent and it catches the light).
	if _adj.is_empty():
		_adj.resize(nodes_rest.size())
		for i in _adj.size():
			_adj[i] = []
		for b in beams:
			(_adj[b[0]] as Array).append(b[1])
			(_adj[b[1]] as Array).append(b[0])
	rot.resize(nodes.size())
	for i in nodes.size():
		var sum := Vector4.ZERO
		var first := Quaternion.IDENTITY
		var n := 0
		for j in _adj[i]:
			var r := nodes_rest[j] - nodes_rest[i]
			var c := nodes[j] - nodes[i]
			if r.length() < 1e-4 or c.length() < 1e-4:
				continue
			var q := Quaternion(r.normalized(), c.normalized())
			if n == 0:
				first = q
			elif first.dot(q) < 0.0:
				q = -q
			sum += Vector4(q.x, q.y, q.z, q.w)
			n += 1
		if n == 0 or sum.length() < 1e-6:
			rot[i] = Quaternion.IDENTITY
		else:
			var s4 := sum.normalized()
			rot[i] = Quaternion(s4.x, s4.y, s4.z, s4.w)


# -- damage -----------------------------------------------------------------------------------------------

func impact(p: Vector3, dir: Vector3, energy: float) -> void:
	## A blow at p (section frame), pushing along dir, with energy (J): the joints near it go in, the tubes
	## drag their neighbours, and what was bent past yield stays bent.
	var fr: Dictionary = std.frame
	if energy < float(fr.min_energy):
		return                                       # (a knock the frame shrugs off)
	var depth := clampf(energy / float(fr.dent_stiffness), 0.0, float(fr.max_dent))
	var r := 0.30 + 0.25 * sqrt(energy / 50000.0)
	var dn := dir.normalized()
	for i in nodes.size():
		var w := exp(-pow(nodes[i].distance_to(p) / r, 2.0))
		if w < 0.01:
			continue
		nodes[i] += dn * depth * w * (0.3 if inv_mass[i] < 0.5 else 1.0)
	_relax(8)
	var yield_s := float(fr.yield_strain)
	var plastic := float(fr.plastic)
	for b in beams:
		var L := nodes[b[0]].distance_to(nodes[b[1]])
		var s := L / float(b[2]) - 1.0
		if absf(s) > yield_s:
			b[2] = lerpf(float(b[2]), L, plastic)            # (bent for good)


func beam_strain(i: int, orig_len: float) -> float:
	## How far a tube is stretched or squeezed from as built.
	var b: Array = beams[i]
	return absf(nodes[b[0]].distance_to(nodes[b[1]]) / orig_len - 1.0)


func _relax(iters: int) -> void:
	for it in iters:
		for b in beams:
			var a: int = b[0]
			var c: int = b[1]
			var d := nodes[c] - nodes[a]
			var L := d.length()
			if L < 1e-6:
				continue
			var wa := inv_mass[a]
			var wc := inv_mass[c]
			var corr := d * ((L - float(b[2])) / L / maxf(wa + wc, 1e-6)) * 0.5
			nodes[a] += corr * wa
			nodes[c] -= corr * wc


func strain(mounts: PackedInt32Array) -> float:
	## The worst stretch or squeeze between any two of a panel's mount joints (0 = as built).
	var worst := 0.0
	for i in mounts.size():
		for j in range(i + 1, mounts.size()):
			var r := nodes_rest[mounts[i]].distance_to(nodes_rest[mounts[j]])
			if r < 0.05:
				continue
			worst = maxf(worst, absf(nodes[mounts[i]].distance_to(nodes[mounts[j]]) / r - 1.0))
	return worst
