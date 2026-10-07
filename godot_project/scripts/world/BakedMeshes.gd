extends Resource
class_name BakedMeshes

## Meshes a builder made once and saved, so a launch loads them in moments instead of building them
## again (remake/tools/bake_world.gd makes them).  `stamp` fingerprints the data they were built from
## (BakedMeshes.fingerprint): a builder uses its bake only while the stamp still matches, and builds
## live otherwise -- a stale bake is never shown.

@export var stamp := ""
@export var keys: Array = []                  # the builder's own key for each mesh
@export var meshes: Array[ArrayMesh] = []
@export var data: Dictionary = {}             # anything else the builder keeps with them


static func fingerprint(paths: Array, version: int) -> String:
	## the builder's version and the MD5 of every file it reads
	var s := str(version)
	for p in paths:
		s += (FileAccess.get_md5(p) if FileAccess.file_exists(p) else "-") + ";"
	return s.md5_text()


## A bake too big for one file (the 20 km ring: the roads alone came to ~97 MB, the git host's limit is 100 MB) is
## saved in parts: <name>.res holds part 0 and data["_parts"], <name>.1.res ... the rest. Meshes are dealt out in
## runs; each Dictionary in data is dealt out by its keys; anything else stays in part 0.
const PART_MB := 40.0


static func part_path(path: String, i: int) -> String:
	return path if i == 0 else "%s.%d.res" % [path.get_basename(), i]


func split(n: int) -> Array:
	var parts := []
	for i in n:
		var p := BakedMeshes.new()
		p.stamp = stamp
		parts.append(p)
	var per := ceili(meshes.size() / float(n))
	for k in meshes.size():
		var p: BakedMeshes = parts[mini(k / maxi(per, 1), n - 1)]
		p.keys.append(keys[k])
		p.meshes.append(meshes[k])
	for dk in data:
		var v = data[dk]
		if v is Dictionary:
			var sub := (v as Dictionary).keys()
			for i in n:
				parts[i].data[dk] = {}
			for k in sub.size():
				parts[k * n / sub.size()].data[dk][sub[k]] = v[sub[k]]
		else:
			parts[0].data[dk] = v
	parts[0].data["_parts"] = n
	return parts


static func load_all(path: String) -> BakedMeshes:
	## the bake at path, its parts merged (null if it's missing or a part is)
	var b := ResourceLoader.load(path) as BakedMeshes
	if b == null:
		return null
	var n: int = b.data.get("_parts", 1)
	for i in range(1, n):
		var p := ResourceLoader.load(part_path(path, i)) as BakedMeshes
		if p == null or p.stamp != b.stamp:
			return null
		b.keys.append_array(p.keys)
		b.meshes.append_array(p.meshes)
		for dk in p.data:
			if p.data[dk] is Dictionary and b.data.get(dk) is Dictionary:
				(b.data[dk] as Dictionary).merge(p.data[dk])
	return b
