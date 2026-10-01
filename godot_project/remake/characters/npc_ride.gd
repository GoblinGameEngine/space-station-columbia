extends RefCounted
class_name NpcRide

## Pose targets for riding in transit (NpcAnimator.ride), in the rider's own frame (-Z forward):
## sitting on a seat (hips on it, feet on the floor ahead, hands on the lap) and standing holding a
## strap (one hand up to it, the other loose). The character's own proportions set them, so a child
## dangles their feet and a tall man's knees come up.
##   animator.ride = NpcRide.seated(npc, seat_height)
##   animator.ride = NpcRide.strap(npc, strap_point_local)


static func _legs(npc: NpcCharacter) -> Vector2:
	var J: Dictionary = npc.built.joints
	var l1 := ((J.LowerLegL as Vector3) - (J.UpperLegL as Vector3)).length()
	var l2 := ((J.FootL as Vector3) - (J.LowerLegL as Vector3)).length()
	return Vector2(l1, l2)


static func seated(npc: NpcCharacter, seat_h: float, slouch := 0.0) -> Dictionary:
	var J: Dictionary = npc.built.joints
	var L := _legs(npc)
	var hips := Vector3(0.0, seat_h + 0.085, 0.04)
	var ank_y := float((J.FootL as Vector3).y)
	var knee_z := hips.z - L.x * 0.95                       # the thighs level, forward from the seat
	var reach := sqrt(maxf(0.0, L.y * L.y - pow(maxf(0.0, (seat_h + 0.02) - ank_y), 2.0)))
	var foot_z := knee_z + 0.05 - minf(reach * 0.25, 0.12)
	var foot_y := maxf(ank_y, seat_h + 0.02 - L.y)          # on the floor, or dangling
	var sep := absf(float((J.UpperLegL as Vector3).x)) * 1.1
	return {"hips": hips, "pitch": -0.05 + slouch, "w": 1.0, "grip": 0.25, "pole": Vector3(0.6, -0.6, -0.2),
		"footL": Vector3(-sep, foot_y, foot_z), "footR": Vector3(sep, foot_y, foot_z),
		"handL": Vector3(-0.13, seat_h + 0.16, knee_z * 0.55), "handR": Vector3(0.13, seat_h + 0.16, knee_z * 0.55)}


static func strap(npc: NpcCharacter, strap_local: Vector3, hand := "R") -> Dictionary:
	## Standing, one hand on a strap (strap_local in the rider's frame; out of reach -> as high as it goes).
	var J: Dictionary = npc.built.joints
	var sh: Vector3 = J["UpperArm" + hand]
	var reach := ((J["Hand" + hand] as Vector3) - sh).length() * 0.97
	var tgt := strap_local
	if (tgt - sh).length() > reach:
		tgt = sh + (tgt - sh).normalized() * reach
	return {"w": 1.0, "grip": 0.9, "pole": Vector3(0.8, -0.3, 0.3), "hand" + hand: tgt}
