extends Node

## NPC AI: the language model that voices the station's people, through an OpenAI-compatible chat
## API (research/npc_ai/llm_options.md).  One provider for now, Groq; PROVIDERS is the table more
## will join (base URL, key page, models), and chat() is provider-blind.
##
## The player brings their own key.  It is kept in user://npc_ai.cfg (the player's own settings
## folder -- never in the project or an exported build).  GROQ_API_KEY in the environment is used
## if no key has been saved.
##
##   var r := await NpcAI.chat([{"role": "system", "content": "..."}, {"role": "user", "content": "Hi"}])
##   if r.ok: print(r.text) else: print(r.error)
##
## Requests are spaced to the free tier's 30 a minute; a 429 is retried once after the wait Groq
## asks for.  Everything runs while the tree is paused (the Communicator pauses it).

signal key_changed

const CONFIG := "user://npc_ai.cfg"
const PROVIDERS := {
	"groq": {
		"name": "Groq",
		"base_url": "https://api.groq.com/openai/v1",
		"key_url": "https://console.groq.com/keys",
		"env": "GROQ_API_KEY",
		"key_prefix": "gsk_",
		"free": "Free: 1,000 replies a day, 30 a minute.  No card needed.",
		# [id, short name, what it's for]
		"models": [
			["qwen/qwen3.8-27b", "Qwen 3.8 27B", "Natural talk (best for NPCs)"],
			["openai/gpt-oss-20b", "GPT-OSS 20B", "Fastest"],
			["openai/gpt-oss-120b", "GPT-OSS 120B", "Smartest, slower"],
		],
	},
}
const MIN_GAP_MS := 2100              # 30 requests a minute
const TIMEOUT_S := 30.0

var provider := "groq"
var model := "qwen/qwen3.8-27b"
var _keys := {}
var _next_slot_ms := 0
var requests_today := 0
var _day := ""
var last_latency_ms := 0


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_load()


# ------------------------------------------------------------------ settings
func _load() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(CONFIG) == OK:
		provider = cfg.get_value("ai", "provider", provider)
		model = cfg.get_value("ai", "model", model)
		for p in PROVIDERS:
			var k: String = cfg.get_value("keys", p, "")
			if k != "":
				_keys[p] = k
		_day = cfg.get_value("usage", "day", "")
		requests_today = cfg.get_value("usage", "count", 0)


func _save() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("ai", "provider", provider)
	cfg.set_value("ai", "model", model)
	for p in _keys:
		cfg.set_value("keys", p, _keys[p])
	cfg.set_value("usage", "day", _day)
	cfg.set_value("usage", "count", requests_today)
	cfg.save(CONFIG)


func info() -> Dictionary:
	return PROVIDERS[provider]


func key() -> String:
	var k: String = _keys.get(provider, "")
	if k == "":
		k = OS.get_environment(info().env)
	return k


func has_key() -> bool:
	return key() != ""


func key_from_env() -> bool:
	return _keys.get(provider, "") == "" and OS.get_environment(info().env) != ""


static func clean_key(raw: String) -> String:
	## Whatever got pasted: trim spaces, newlines and quotes; drop "Bearer " or a "GROQ_API_KEY=" prefix.
	var k := raw.strip_edges().replace("\n", "").replace("\r", "").replace(" ", "")
	k = k.trim_prefix("\"").trim_suffix("\"").trim_prefix("'").trim_suffix("'")
	if k.to_lower().begins_with("bearer"):
		k = k.substr(6)
	var eq := k.find("=")
	if eq >= 0 and eq < 24:
		k = k.substr(eq + 1)
	return k.strip_edges()


func looks_like_key(k: String) -> bool:
	var pre: String = info().get("key_prefix", "")
	return k.length() >= 20 and (pre == "" or k.begins_with(pre))


func set_key(raw: String) -> String:
	var k := clean_key(raw)
	if k == "":
		_keys.erase(provider)
	else:
		_keys[provider] = k
	_save()
	key_changed.emit()
	return k


func clear_key() -> void:
	_keys.erase(provider)
	_save()
	key_changed.emit()


func masked_key() -> String:
	var k := key()
	if k.length() < 12:
		return "(none)"
	return k.substr(0, 4) + "..." + k.substr(k.length() - 4)


func set_model(id: String) -> void:
	model = id
	_save()


func base_url() -> String:
	## NPC_AI_BASE_URL overrides the provider's (tests point it at a local stand-in server)
	var o := OS.get_environment("NPC_AI_BASE_URL")
	return o if o != "" else String(info().base_url)


# ------------------------------------------------------------------ requests
func _count_request() -> void:
	var today := Time.get_date_string_from_system()
	if today != _day:
		_day = today
		requests_today = 0
	requests_today += 1
	_save()


func _wait_for_slot() -> void:
	## Space requests MIN_GAP_MS apart (the free tier's per-minute limit).
	var now := Time.get_ticks_msec()
	var at := maxi(now, _next_slot_ms)
	_next_slot_ms = at + MIN_GAP_MS
	if at > now:
		await get_tree().create_timer((at - now) / 1000.0, true, false, true).timeout


func _http(method: HTTPClient.Method, path: String, body := "") -> Dictionary:
	## {code, headers, text, net_error} -- net_error is the HTTPRequest result when it isn't RESULT_SUCCESS
	var req := HTTPRequest.new()
	req.process_mode = Node.PROCESS_MODE_ALWAYS
	req.timeout = TIMEOUT_S
	add_child(req)
	var headers := PackedStringArray(["Authorization: Bearer " + key(), "Content-Type: application/json",
		"User-Agent: SpaceStationColumbia/1.0"])
	var err := req.request(base_url() + path, headers, method, body)
	if err != OK:
		req.queue_free()
		return {"code": 0, "headers": PackedStringArray(), "text": "", "net_error": err}
	var res: Array = await req.request_completed
	req.queue_free()
	return {"code": res[1], "headers": res[2], "text": (res[3] as PackedByteArray).get_string_from_utf8(),
		"net_error": -1 if res[0] == HTTPRequest.RESULT_SUCCESS else res[0]}


static func _header(headers: PackedStringArray, name: String) -> String:
	for h in headers:
		var i := h.find(":")
		if i > 0 and h.substr(0, i).strip_edges().to_lower() == name:
			return h.substr(i + 1).strip_edges()
	return ""


func _friendly(r: Dictionary) -> String:
	var pname: String = info().name
	if r.net_error != -1:
		match r.net_error:
			HTTPRequest.RESULT_TIMEOUT:
				return "%s took too long to answer." % pname
			HTTPRequest.RESULT_CANT_RESOLVE, HTTPRequest.RESULT_CANT_CONNECT, HTTPRequest.RESULT_CONNECTION_ERROR:
				return "Can't reach %s.  Is the internet connected?" % pname
			HTTPRequest.RESULT_TLS_HANDSHAKE_ERROR:
				return "Secure connection to %s failed." % pname
			_:
				return "Network error (%d)." % r.net_error
	var msg := ""
	var j = JSON.parse_string(r.text)
	if j is Dictionary and j.has("error"):
		var e = j.error
		msg = String(e.get("message", "")) if e is Dictionary else str(e)
	match int(r.code):
		401, 403:
			return "%s didn't accept the key.  Check it was pasted whole." % pname
		404:
			return "%s doesn't offer that model any more.  Pick another." % pname
		413:
			return "The conversation got too long for the model."
		429:
			return "%s's free limit is reached for now.  Try again in a minute." % pname
		500, 502, 503:
			return "%s is having trouble right now.  Try again shortly." % pname
	return ("%s said: %s" % [pname, msg]) if msg != "" else ("%s answered with error %d." % [pname, r.code])


func test_connection() -> Dictionary:
	## {ok, message, models: [ids]} -- checks the key by listing the provider's models (costs no tokens)
	if not has_key():
		return {"ok": false, "message": "No key yet.", "models": []}
	var r := await _http(HTTPClient.METHOD_GET, "/models")
	if r.net_error != -1 or r.code != 200:
		return {"ok": false, "message": _friendly(r), "models": []}
	var ids := []
	var j = JSON.parse_string(r.text)
	if j is Dictionary:
		for m in j.get("data", []):
			ids.append(String(m.get("id", "")))
	var has := ids.has(model)
	return {"ok": true, "models": ids,
		"message": "Connected to %s.  %d models available%s." % [info().name, ids.size(),
			"" if has or ids.is_empty() else "; the chosen model isn't one of them"]}


func _model_params(id: String) -> Dictionary:
	## Answer straight away: no visible reasoning, as little hidden reasoning as the model allows
	if id.begins_with("openai/gpt-oss"):
		return {"reasoning_effort": "low", "include_reasoning": false}
	if id.begins_with("qwen/"):
		return {"reasoning_effort": "none", "reasoning_format": "hidden"}
	return {}


func chat(messages: Array, opts := {}) -> Dictionary:
	## One reply.  opts: max_tokens (160), temperature (0.8), model.
	## Returns {ok, text, error, latency_ms, usage}.
	if not has_key():
		return {"ok": false, "text": "", "error": "No %s key.  Add one in the NPC AI app." % info().name, "latency_ms": 0, "usage": {}}
	var mid: String = opts.get("model", model)
	var body := {"model": mid, "messages": messages, "max_tokens": int(opts.get("max_tokens", 160)),
		"temperature": float(opts.get("temperature", 0.8))}
	body.merge(_model_params(mid))
	var payload := JSON.stringify(body)
	for attempt in 2:
		await _wait_for_slot()
		var t0 := Time.get_ticks_msec()
		var r := await _http(HTTPClient.METHOD_POST, "/chat/completions", payload)
		last_latency_ms = Time.get_ticks_msec() - t0
		if r.net_error == -1 and r.code == 429 and attempt == 0:
			var wait := clampf(_header(r.headers, "retry-after").to_float(), 1.0, 10.0)
			await get_tree().create_timer(wait, true, false, true).timeout
			continue
		if r.net_error != -1 or r.code != 200:
			return {"ok": false, "text": "", "error": _friendly(r), "latency_ms": last_latency_ms, "usage": {}}
		_count_request()
		var j = JSON.parse_string(r.text)
		var text := ""
		if j is Dictionary and not (j.get("choices", []) as Array).is_empty():
			text = String(j.choices[0].get("message", {}).get("content", ""))
		# a model that still thinks aloud: keep what follows its reasoning
		var close := text.rfind("</think>")
		if close >= 0:
			text = text.substr(close + 8)
		return {"ok": text.strip_edges() != "", "text": text.strip_edges(),
			"error": "" if text.strip_edges() != "" else "The model returned an empty reply.",
			"latency_ms": last_latency_ms, "usage": j.get("usage", {}) if j is Dictionary else {}}
	return {"ok": false, "text": "", "error": "%s's free limit is reached for now." % info().name, "latency_ms": 0, "usage": {}}
