extends Area3D
class_name RemakeInteractZone

## Somewhere to aim the use key at that isn't a solid thing: a vehicle's open doorway (use it to
## close the doors), its steering wheel or yoke (use it to drive).  An area on its own layer
## (LAYER), so it blocks no one's way and no shot -- only the player's use ray looks for it
## (StationPlayer._try_interact).

const LAYER := 1 << 12

var gives_way := false               # a doorway: anything usable seen through it comes first
var on_interact: Callable            # (by: Node) -> String
var prompt: Callable                 # () -> String


static func make(parent: Node3D, zone_name: String, at: Transform3D, size: Vector3, act: Callable, say: Callable) -> RemakeInteractZone:
	var z := RemakeInteractZone.new()
	z.name = zone_name
	z.on_interact = act
	z.prompt = say
	z.collision_layer = LAYER
	z.collision_mask = 0
	z.monitoring = false
	z.monitorable = true                   # (a ray only finds an area that is)
	parent.add_child(z)
	z.transform = at
	var cs := CollisionShape3D.new()
	var box := BoxShape3D.new()
	box.size = size
	cs.shape = box
	z.add_child(cs)
	return z


func interact(by: Node = null) -> String:
	return on_interact.call(by) if on_interact.is_valid() else ""


func interact_prompt() -> String:
	return prompt.call() if prompt.is_valid() else ""
