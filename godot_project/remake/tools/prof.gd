extends RefCounted
class_name Prof

## Section timers for the performance work: Prof.begin("tram.place") ... Prof.end("tram.place").
## Off unless Prof.on is set (one bool test each call); PerfProbe reads and clears the totals.

static var on := false
static var _t0 := {}
static var total := {}               # name -> [usec, calls]


static func begin(name: String) -> void:
	if on:
		_t0[name] = Time.get_ticks_usec()


static func end(name: String) -> void:
	if on and _t0.has(name):
		var a: Array = total.get(name, [0, 0])
		a[0] += Time.get_ticks_usec() - int(_t0[name])
		a[1] += 1
		total[name] = a


static func report(frames: int) -> Dictionary:
	## ms per frame and calls per frame of each section, then cleared.
	var out := {}
	for k in total:
		out[k] = [snappedf(float(total[k][0]) / 1000.0 / maxi(frames, 1), 0.01), snappedf(float(total[k][1]) / maxi(frames, 1), 0.1)]
	total.clear()
	return out
