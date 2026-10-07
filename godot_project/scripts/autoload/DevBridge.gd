extends Node

# A local-only command server for driving/inspecting a RUNNING game
# instance from the outside (Claude's shell, not the human player) --
# built specifically to stop relying on xdotool key/mouse simulation +
# scrot screenshots + guessing pixel coordinates for everything, which is
# slow, imprecise, and breaks entirely if the desktop session locks (all
# of which happened in the session that led to building this).
#
# Debug-only (see _ready()) -- never listens in an exported release
# build (verified live: grepped an actual --export-release build's boot
# log for any mention of this file, found none). Listens on 127.0.0.1
# only, never any external interface.
#
# SECURITY: the debug-only + localhost-only gates above are necessary
# but were NOT sufficient on their own -- the protocol itself had no
# authentication, meaning ANY other local process (a compromised
# dependency, browser extension, or another agent already running as
# you) could connect and run arbitrary GDScript via `run`/`eval` in any
# debug build, with full FileAccess (unsandboxed read/write) and no
# audit trail. Fixed with a per-launch random token (below): generated
# fresh every time the game starts (so nothing long-lived can leak) and
# written to a local file only this machine's own user can read; every
# command except `ping` must include it. Real cost of this: near zero
# (gcmd.py reads the same file automatically) -- there was no reason not
# to have this from the start, and there's even less reason as this
# pattern spreads to other people's projects with less scrutiny than a
# single dev's own machine.
#
# Protocol: connect a TCP socket to 127.0.0.1:PORT, send ONE line of JSON
# (a command object, plus a "token" field -- see AUTH below) terminated
# by "\n", read back ONE line of JSON (the response), connection closes
# after that. See tools/gcmd.py (outside this project, in
# ~/goblin-engine/tools/) for the client half.
#
# Commands (each is {"cmd": "<name>", ...fields}):
#   ping                                        -> {"ok": true, "result": "pong"}
#   help                                        -> {"ok": true, "result": [<this list>]}
#   eval        {"code": "<one expression>"}    -> evaluates via Expression, base
#                                                   instance = this node, so
#                                                   get_tree()/get_node() etc. work
#                                                   unqualified. Autoloads: address
#                                                   as get_node("/root/QuestManager").
#   run         {"code": "<gdscript statements>"} -> code becomes the BODY of
#                                                   `func run(root: Node):` on a
#                                                   throwaway RefCounted script --
#                                                   `root` is the SceneTree root
#                                                   (i.e. root.get_node("/root/Main"),
#                                                   root.get_node("/root/QuestManager")).
#                                                   Write a `return` to get a value
#                                                   back. This is the main way to
#                                                   drive GameMenu/Hud
#                                                   etc. precisely -- call their own
#                                                   methods directly instead of
#                                                   simulating clicks on them.
#   screenshot  {"path": "/abs/path.png"}       -> saves the current rendered frame.
#                                                   Reads the real framebuffer, so it
#                                                   works even if the OS desktop is
#                                                   locked/obscured (unlike scrot).
#   dump_tree   {"path": "/root", "max_depth": 4} -> node names/types/paths, plus
#                                                   position+size+text for Controls --
#                                                   for finding a button's real
#                                                   coordinates instead of guessing
#                                                   from a screenshot.
#   key         {"physical_keycode": 4194333, "pressed": true, "ctrl"/"shift"/"alt": false}
#   key_tap     {"physical_keycode": 4194333, ...}   -> press then release
#   press_action / release_action  {"action": "jump"} -> Input.action_press/release
#   mouse_button {"button_index": 1, "pressed": true, "x":.., "y":..}
#   mouse_click  {"button_index": 1, "x":.., "y":..}  -> press then release
#   mouse_motion {"x":.., "y":.., "dx":.., "dy":..}   -> for camera-look drags;
#                                                        dx/dy is the RELATIVE delta,
#                                                        constructed directly (no OS
#                                                        cursor-warp synthetic-delta
#                                                        issue the way xdotool has)
#   mouse_wheel  {"direction": "up"|"down", "steps": 1, "x":.., "y":..}
#   query        {"op": "near"|"find"|"ground"|"view"|"check"|"here", "args": [...]} -> text: where things are,
#                                                   without rendering (scripts/autoload/WorldQuery.gd)
#   quit                                        -> get_tree().quit()
#   wait_frame  {"count": 1}                    -> blocks (via await, not
#                                                   wall-clock sleep) until
#                                                   `count` more frames
#                                                   have actually rendered,
#                                                   returns the new total
#                                                   frame count. Replaces
#                                                   guessing a sleep
#                                                   duration before a
#                                                   screenshot/read_pixels.
#   read_pixels {"points": [[x,y], ...]}        -> RGBA (0-255 ints) of
#                                                   each pixel in the
#                                                   CURRENTLY DISPLAYED
#                                                   frame, no PNG/PIL
#                                                   round-trip needed.
#   reload_shader {"node_path": "...", "shader_path": "res://..."} ->
#                                                   true hot-reload: re-
#                                                   reads the .gdshader
#                                                   file and recompiles it
#                                                   IN PLACE on the Shader
#                                                   object node_path's
#                                                   material_override
#                                                   already holds -- no
#                                                   relaunch, every other
#                                                   material sharing that
#                                                   same Shader resource
#                                                   updates too.
#
# Every response is {"ok": true, "result": <json-safe value or omitted>,
# "result_str": str(value)} or {"ok": false, "error": "..."}.
#
# AUTH: every command except "ping" must carry a top-level "token" field
# matching a random string generated fresh at each launch and written to
# a local file (see TOKEN_PATH_ENV below) that only this OS user can
# read. gcmd.py reads that same file automatically -- nothing to
# configure for the normal workflow. Deliberately NOT a fixed/checked-in
# secret: a new token every launch means an old, leaked, or logged token
# is worthless the next time the game starts.

const PORT_ENV := "GOBLINS_DEV_BRIDGE_PORT"
const DEFAULT_PORT := 8765
# Where the per-launch token gets written -- a real path, not user://,
# specifically so an EXTERNAL process (gcmd.py, plain Python, no Godot
# APIs available) can compute the identical path independently without
# having to duplicate Godot's project-name-dependent user-data-dir
# resolution. Overridable via env var the same way PORT_ENV is, and
# namespaced by port so multiple instances on different ports (see
# PORT_ENV) don't clobber each other's token file.
const TOKEN_PATH_ENV := "GOBLINS_DEV_BRIDGE_TOKEN_FILE"

const COMMAND_NAMES := [
	"ping", "help", "eval", "run", "screenshot", "dump_tree",
	"key", "key_tap", "press_action", "release_action",
	"mouse_button", "mouse_click", "mouse_motion", "mouse_wheel", "quit",
	"wait_frame", "read_pixels", "reload_shader", "query",
]

var _server := TCPServer.new()
var _peers: Array = []   # [{peer: StreamPeerTCP, buffer: String}]
var _port := DEFAULT_PORT
var _token := ""
var _token_path := ""


func _token_path_for(port: int) -> String:
	var override := OS.get_environment(TOKEN_PATH_ENV)
	if override != "":
		return override
	var tmp_dir := OS.get_environment("TMPDIR")
	if tmp_dir == "":
		tmp_dir = "/tmp"
	return "%s/goblins_devbridge_%d.token" % [tmp_dir.rstrip("/"), port]


func _generate_token() -> String:
	var rng := RandomNumberGenerator.new()
	rng.randomize()
	const CHARS := "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
	var s := ""
	for i in range(40):
		s += CHARS[rng.randi() % CHARS.length()]
	return s


func _ready() -> void:
	if not OS.is_debug_build():
		return
	process_mode = Node.PROCESS_MODE_ALWAYS
	var env_port := OS.get_environment(PORT_ENV)
	if env_port != "" and env_port.is_valid_int():
		_port = int(env_port)
	_token = _generate_token()
	_token_path = _token_path_for(_port)
	var f := FileAccess.open(_token_path, FileAccess.WRITE)
	if f:
		f.store_string(_token)
		f.close()
		# Best-effort on POSIX -- restricts the token file to this OS
		# user only. If this fails (e.g. non-POSIX platform) the token
		# still rotates every launch, which remains the primary defense.
		OS.execute("chmod", ["600", _token_path])
	else:
		push_warning("DevBridge: could not write token file to %s -- refusing to start unauthenticated" % _token_path)
		return
	var err := _server.listen(_port, "127.0.0.1")
	if err != OK:
		push_warning("DevBridge: could not listen on 127.0.0.1:%d (error %d)" % [_port, err])
		return
	print("DevBridge: listening on 127.0.0.1:%d (auth token: %s)" % [_port, _token_path])


func _process(_delta: float) -> void:
	if not _server.is_listening():
		return
	while _server.is_connection_available():
		_peers.append({"peer": _server.take_connection(), "buffer": "", "dispatched": false})

	var still_alive: Array = []
	for entry in _peers:
		var peer: StreamPeerTCP = entry["peer"]
		peer.poll()
		if peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
			continue   # dropped -- don't keep it (also how a completed
			           # async dispatch's own disconnect_from_host() gets
			           # this entry finally dropped, one tick later)
		if entry["dispatched"]:
			still_alive.append(entry)   # response is in flight via an
			                             # awaited coroutine -- just keep
			                             # the connection alive, nothing
			                             # more to read from this peer
			continue
		var avail := peer.get_available_bytes()
		if avail > 0:
			var chunk_result: Array = peer.get_partial_data(avail)
			if chunk_result[0] == OK:
				entry["buffer"] += (chunk_result[1] as PackedByteArray).get_string_from_utf8()
			var nl: int = entry["buffer"].find("\n")
			if nl != -1:
				var line: String = entry["buffer"].substr(0, nl)
				entry["dispatched"] = true
				_dispatch_async(line, peer)   # fire-and-forget: most
				                               # commands resolve
				                               # synchronously within
				                               # this SAME frame (no
				                               # behavior change from
				                               # before); "wait_frame"
				                               # is the one that
				                               # actually spans real
				                               # frames, via `await`.
		still_alive.append(entry)
	_peers = still_alive


func _dispatch_async(line: String, peer: StreamPeerTCP) -> void:
	var response := await _dispatch_line(line)
	if peer.get_status() == StreamPeerTCP.STATUS_CONNECTED:
		peer.put_data((response + "\n").to_utf8_buffer())
		peer.disconnect_from_host()


func _dispatch_line(line: String) -> String:
	var req = JSON.parse_string(line)
	if typeof(req) != TYPE_DICTIONARY or not req.has("cmd"):
		return JSON.stringify({"ok": false, "error": "expected a JSON object with a \"cmd\" field, got: %s" % line})
	var result = await _handle(req)
	return JSON.stringify(result)


func _handle(req: Dictionary) -> Dictionary:
	var cmd: String = req.get("cmd", "")
	# "ping" alone skips auth -- harmless (just echoes "pong"), and lets
	# a client confirm the port is even up before it needs to have found
	# the token file yet.
	if cmd != "ping" and String(req.get("token", "")) != _token:
		return {"ok": false, "error": "missing or incorrect auth token (see %s)" % _token_path}
	match cmd:
		"ping":
			return {"ok": true, "result": "pong"}
		"help":
			return {"ok": true, "result": COMMAND_NAMES}
		"eval":
			return _cmd_eval(req.get("code", ""))
		"run":
			return _cmd_run(req.get("code", ""))
		"screenshot":
			return _cmd_screenshot(req.get("path", ""))
		"dump_tree":
			return _cmd_dump_tree(req.get("path", "/root"), int(req.get("max_depth", 4)))
		"key":
			return _cmd_key(req)
		"key_tap":
			_cmd_key(_with(req, "pressed", true))
			_cmd_key(_with(req, "pressed", false))
			return {"ok": true}
		"press_action":
			Input.action_press(StringName(req.get("action", "")))
			return {"ok": true}
		"release_action":
			Input.action_release(StringName(req.get("action", "")))
			return {"ok": true}
		"mouse_button":
			return _cmd_mouse_button(req)
		"mouse_click":
			_cmd_mouse_button(_with(req, "pressed", true))
			_cmd_mouse_button(_with(req, "pressed", false))
			return {"ok": true}
		"mouse_motion":
			return _cmd_mouse_motion(req)
		"mouse_wheel":
			return _cmd_mouse_wheel(req)
		"quit":
			call_deferred("_do_quit")
			return {"ok": true}
		"wait_frame":
			return await _cmd_wait_frame(int(req.get("count", 1)))
		"read_pixels":
			return _cmd_read_pixels(req.get("points", []))
		"reload_shader":
			return _cmd_reload_shader(req.get("node_path", ""), req.get("shader_path", ""))
		"query":
			# where things are, as text (WorldQuery: near, find, ground, view, check, here)
			return {"ok": true, "result": WorldQuery.run(str(req.get("op", "here")), req)}
		_:
			return {"ok": false, "error": "unknown cmd '%s' -- see 'help'" % cmd}


## Blocks (via await, not a busy-loop -- costs nothing between frames)
## until `count` more frames have actually been drawn, then returns the
## new frame count. Built specifically to replace guessed `sleep 0.5`
## calls before every screenshot this session -- those were sometimes
## too short (a stale frame) and always at least somewhat wasteful.
## Godot's own frame counter (Engine.get_frames_drawn()) is the ground
## truth for "has a new frame actually rendered," not wall-clock time.
func _cmd_wait_frame(count: int) -> Dictionary:
	count = max(1, count)
	for i in range(count):
		await get_tree().process_frame
	return {"ok": true, "result": Engine.get_frames_drawn()}


## Reads back exact pixel colors from the CURRENTLY DISPLAYED frame --
## built to replace the save-PNG-then-decode-with-PIL-in-a-second-process
## workflow that every hard bug this session actually got root-caused
## with (screenshot -> external Python -> Image.getpixel() in a loop).
## Same information, no round-trip through disk or a second process.
## `points`: a list of [x, y] pixel coordinates. Returns RGBA 0-255 ints
## per point (matching PIL's convention, since that's what every
## debug-readback script this session wrote already expected).
func _cmd_read_pixels(points) -> Dictionary:
	if typeof(points) != TYPE_ARRAY:
		return {"ok": false, "error": "'points' must be a list of [x, y] pairs"}
	var img := get_viewport().get_texture().get_image()
	var out: Array = []
	for p in points:
		if typeof(p) != TYPE_ARRAY or p.size() != 2:
			return {"ok": false, "error": "each point must be [x, y], got: %s" % str(p)}
		var x: int = int(p[0])
		var y: int = int(p[1])
		if x < 0 or y < 0 or x >= img.get_width() or y >= img.get_height():
			out.append(null)
			continue
		var c := img.get_pixel(x, y)
		out.append([roundi(c.r * 255), roundi(c.g * 255), roundi(c.b * 255), roundi(c.a * 255)])
	return {"ok": true, "result": out}


## True shader hot-reload -- no relaunch, no --headless --import, no
## resetting camera position/time-of-day to get back to the test state.
## The key fact this relies on: Shader.code is a live, settable String
## property on the SAME Shader resource object every material referencing
## it already holds -- overwriting it (from the .gdshader file's current
## on-disk contents) recompiles that object'S ACTUAL SHADER IN PLACE,
## which is exactly what the Godot editor's own live shader preview does
## under the hood. This is NOT loading a fresh Shader resource (that
## would need every material's `.shader` reference retargeted, and
## wouldn't affect one already `preload()`-baked into running code) --
## it mutates the one they all already point to.
## `node_path`: a node with a ShaderMaterial in `material_override`
## (MeshInstance3D, MultiMeshInstance3D, or similar).
## `shader_path`: the .gdshader file to re-read from disk (usually the
## same one the material's shader was originally loaded from, but not
## required to be -- this is a generic "recompile this material's
## shader from this file's current text" operation).
##
## Verified live, both directions: changing actual fragment() LOGIC
## (confirmed by making it paint the whole screen solid red) takes effect
## immediately, no relaunch. One real caveat found in that same test:
## changing ONLY a `uniform ... = <default>` value did NOT visibly
## change anything, even though the recompile itself succeeded -- Godot
## appears to snapshot a ShaderMaterial's effective uniform values at the
## point the shader is first ASSIGNED to it, and a bare code-level
## default change doesn't retroactively refresh a value the material
## never explicitly overrode. If iterating on a plain tunable constant
## rather than logic, call set_shader_parameter() directly instead (or
## through this same DevBridge connection via `run`) -- this command is
## for shader CODE changes.
func _cmd_reload_shader(node_path: String, shader_path: String) -> Dictionary:
	var node := get_node_or_null(node_path)
	if node == null:
		return {"ok": false, "error": "no node at %s" % node_path}
	if not ("material_override" in node) or node.material_override == null:
		return {"ok": false, "error": "%s has no material_override" % node_path}
	var mat: Material = node.material_override
	if not (mat is ShaderMaterial):
		return {"ok": false, "error": "%s's material_override is not a ShaderMaterial" % node_path}
	var f := FileAccess.open(shader_path, FileAccess.READ)
	if f == null:
		return {"ok": false, "error": "could not open %s (error %d)" % [shader_path, FileAccess.get_open_error()]}
	var src := f.get_as_text()
	f.close()
	(mat as ShaderMaterial).shader.code = src
	return {"ok": true, "result": "reloaded %s onto %s" % [shader_path, node_path]}


func _do_quit() -> void:
	get_tree().quit()


func _with(d: Dictionary, key: String, value) -> Dictionary:
	var d2 := d.duplicate()
	d2[key] = value
	return d2


## Wraps a raw GDScript value for the JSON response: JSON.stringify()
## can't serialize arbitrary Objects/Vector3/etc., so the human/JSON-safe
## "result" field is only included for types it actually supports --
## "result_str" (via GDScript's own str()) always works and is usually
## enough to just read the answer.
func _wrap_result(value) -> Dictionary:
	var out := {"ok": true, "result_str": str(value)}
	match typeof(value):
		TYPE_NIL, TYPE_BOOL, TYPE_INT, TYPE_FLOAT, TYPE_STRING, TYPE_ARRAY, TYPE_DICTIONARY:
			out["result"] = value
	return out


func _cmd_eval(code: String) -> Dictionary:
	var expr := Expression.new()
	var err := expr.parse(code, [])
	if err != OK:
		return {"ok": false, "error": "parse error: %s" % expr.get_error_text()}
	var result = expr.execute([], self, true)
	if expr.has_execute_failed():
		return {"ok": false, "error": "execution failed -- see the game's own log for details"}
	return _wrap_result(result)


## Multi-statement code, unlike eval's single expression. Inserted as the
## indented body of a function on a throwaway script -- write it exactly
## as you would inside that function (your own nested blocks need their
## own relative indentation, same as any GDScript function body), and
## write `return ...` if you want a value back.
func _cmd_run(code: String) -> Dictionary:
	var src := "extends RefCounted\nfunc run(root: Node):\n"
	for line in code.split("\n"):
		src += "\t" + line + "\n"
	var script := GDScript.new()
	script.source_code = src
	var err := script.reload()
	if err != OK:
		return {"ok": false, "error": "GDScript compile error (code %d) -- see the game's own log for the exact line/message" % err}
	var instance = script.new()
	var result = instance.run(get_tree().root)
	return _wrap_result(result)


func _cmd_screenshot(path: String) -> Dictionary:
	if path == "":
		return {"ok": false, "error": "missing 'path'"}
	var img := get_viewport().get_texture().get_image()
	var err := img.save_png(path)
	if err != OK:
		return {"ok": false, "error": "save_png failed with code %d" % err}
	return {"ok": true, "result": path}


func _cmd_dump_tree(path: String, max_depth: int) -> Dictionary:
	var start := get_node_or_null(path)
	if start == null:
		return {"ok": false, "error": "no node at path '%s'" % path}
	return {"ok": true, "result": _dump_node(start, 0, max_depth)}


func _dump_node(node: Node, depth: int, max_depth: int) -> Dictionary:
	var d := {"name": String(node.name), "type": node.get_class()}
	if node is Control:
		var c := node as Control
		d["rect"] = [c.global_position.x, c.global_position.y, c.size.x, c.size.y]
		d["visible"] = c.visible
		for prop in ["text", "title"]:
			if prop in node:
				d[prop] = node.get(prop)
	elif node is Node3D:
		d["global_position"] = var_to_str((node as Node3D).global_position)
	if depth < max_depth:
		var children := []
		for c in node.get_children():
			children.append(_dump_node(c, depth + 1, max_depth))
		if not children.is_empty():
			d["children"] = children
	return d


func _cmd_key(data: Dictionary) -> Dictionary:
	var ev := InputEventKey.new()
	var code := int(data.get("physical_keycode", data.get("keycode", 0)))
	ev.physical_keycode = code
	ev.keycode = int(data.get("keycode", code))
	ev.pressed = data.get("pressed", true)
	ev.ctrl_pressed = data.get("ctrl", false)
	ev.shift_pressed = data.get("shift", false)
	ev.alt_pressed = data.get("alt", false)
	ev.echo = data.get("echo", false)
	Input.parse_input_event(ev)
	return {"ok": true}


func _cmd_mouse_button(data: Dictionary) -> Dictionary:
	var ev := InputEventMouseButton.new()
	ev.button_index = int(data.get("button_index", MOUSE_BUTTON_LEFT))
	ev.pressed = data.get("pressed", true)
	ev.position = Vector2(float(data.get("x", 0.0)), float(data.get("y", 0.0)))
	ev.global_position = ev.position
	Input.parse_input_event(ev)
	return {"ok": true}


func _cmd_mouse_motion(data: Dictionary) -> Dictionary:
	var ev := InputEventMouseMotion.new()
	ev.position = Vector2(float(data.get("x", 0.0)), float(data.get("y", 0.0)))
	ev.relative = Vector2(float(data.get("dx", 0.0)), float(data.get("dy", 0.0)))
	Input.parse_input_event(ev)
	return {"ok": true}


func _cmd_mouse_wheel(data: Dictionary) -> Dictionary:
	var idx := MOUSE_BUTTON_WHEEL_UP if data.get("direction", "up") == "up" else MOUSE_BUTTON_WHEEL_DOWN
	var steps := int(data.get("steps", 1))
	for i in range(steps):
		_cmd_mouse_button({"button_index": idx, "pressed": true, "x": data.get("x", 0.0), "y": data.get("y", 0.0)})
		_cmd_mouse_button({"button_index": idx, "pressed": false, "x": data.get("x", 0.0), "y": data.get("y", 0.0)})
	return {"ok": true}
