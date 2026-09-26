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
