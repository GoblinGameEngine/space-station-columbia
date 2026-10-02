extends Node
class_name PerfProbe

## Frame-cost measurement for the performance work (the user, 2026-10-01: "60fps regardless if the
## tram or traffic is visible"). Run from DevBridge:
##   var p = PerfProbe.new(); root.add_child(p); p.sample(120)        -> p.done, p.result
##   PerfProbe.toggle(root, "Roads", false)                          (hide a system to see its cost)
## A sample averages, over n frames: the frame time (ms), the main thread's process and physics time,
## the render thread's CPU time and the GPU's (RenderingServer's measured viewport times), draw calls,
## objects and primitives drawn.

var done := true
var result := {}
var _n := 0
var _left := 0
var _acc := {}


func sample(n: int) -> void:
	var vp := get_viewport().get_viewport_rid()
	RenderingServer.viewport_set_measure_render_time(vp, true)
	_n = n
	_left = n + 10                    # (the first frames after a change settle)
	_acc = {}
	Prof.total.clear()
	done = false


func _process(delta: float) -> void:
	if done:
		return
	_left -= 1
	if _left > _n:
		return
	if _left == _n:
		Prof.total.clear()
		Prof.on = true
	var vp := get_viewport().get_viewport_rid()
	var m := {
		"frame_ms": delta * 1000.0,
		"process_ms": Performance.get_monitor(Performance.TIME_PROCESS) * 1000.0,
		"physics_ms": Performance.get_monitor(Performance.TIME_PHYSICS_PROCESS) * 1000.0,
		"render_cpu_ms": RenderingServer.viewport_get_measured_render_time_cpu(vp) + RenderingServer.get_frame_setup_time_cpu(),
		"gpu_ms": RenderingServer.viewport_get_measured_render_time_gpu(vp),
		"draws": float(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)),
		"objects": float(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_OBJECTS_IN_FRAME)),
		"prims": float(RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)),
		"nodes": float(Performance.get_monitor(Performance.OBJECT_NODE_COUNT)),
	}
	for k in m:
		_acc[k] = float(_acc.get(k, 0.0)) + m[k]
	if _left <= 0:
		result = {}
		for k in _acc:
			result[k] = snappedf(float(_acc[k]) / _n, 0.01)
		result["fps"] = snappedf(1000.0 / maxf(float(result.frame_ms), 0.001), 0.1)
		Prof.on = false
		result["sections"] = Prof.report(_n)
		done = true


static func toggle(root: Node, path: String, on: bool) -> void:
	## Show or hide a system under RemakeStation (and stop its processing while hidden).
	var n := root.get_node_or_null("RemakeStation/" + path)
	if n == null:
		return
	if n is Node3D:
		(n as Node3D).visible = on
	n.process_mode = Node.PROCESS_MODE_INHERIT if on else Node.PROCESS_MODE_DISABLED
