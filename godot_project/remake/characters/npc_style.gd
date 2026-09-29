extends RefCounted
class_name NpcStyle

## How a person moves, from who they are (research/animation/expressive_motion.md):
##   personality (Big Five) -> Laban Effort (Space, Weight, Time, Flow) by the PERFORM matrix
##   (Durupinar, Neff, Badler et al., ACM TOG: measured in perception studies), then Effort ->
##   motion parameters by PERFORM's regression (Table IV) where it has one, and by Laban's own
##   affinities where it doesn't;
##   mood -> the emotion-in-gait features of Roether et al. 2009 (head inclination for sadness,
##   elbow flexion for anger and fear, larger movement for happy and angry, smaller for sad and
##   afraid);
##   age and body -> the gait changes of research/animation/gait_reference.md.
## Effort values are in [-1, 1], negative = the indulging pole: Indirect, Light, Sustained, Free.

# rows Space, Weight, Time, Flow; columns O, C, E, A, N
const NPE := [
	[-0.921, 0.928, -0.894, 0.0, -1.0],
	[0.0, 0.0, 0.0, -1.0, 0.0],
	[0.0, -0.857, 0.99, -1.0, 0.97],
	[-0.931, 0.938, -1.0, 0.0, -0.762]]
const OCEAN := ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]


static func effort(personality: Dictionary) -> Vector4:
	## PERFORM step 1: per Effort, the strongest pull each way (not a plain sum).
	var p := []
	for k in OCEAN:
		p.append(clampf(float(personality.get(k, 0.5)) * 2.0 - 1.0, -1.0, 1.0))
	var e := Vector4()
	for i in 4:
		var pos := 0.0
		var neg := 0.0
		for j in 5:
			var x: float = NPE[i][j] * p[j]
			pos = maxf(pos, x)
			neg = minf(neg, x)
		e[i] = pos + neg
	return e


static func params(v: Dictionary, mood := "neutral") -> Dictionary:
	## Everything the animator needs to move this person their way.
	var e := effort(v.get("personality", {}))
	var space := e.x
	var weight := e.y
	var time_e := e.z
	var flow := e.w
	var age := float(v.get("age", 30))
	var b: Array = v.get("build", [0.43, 0.27, 0.30])
	var heavy := float(b[2])
	var elder := smoothstep(58.0, 85.0, age)
	var child := 1.0 - smoothstep(6.0, 14.0, age)
	var g: Array = v.get("gait", [1.0, 1.0, 1.0, 1.0])
	var s := {
		"effort": e,
		# PERFORM Table IV (scaled round our neutral): Sudden moves faster; Free overshoots and turns
		# the torso more; Indirect looks about more, and more often; Strong anticipates and sinks;
		# Light breathes bigger and rises
		"speed": 1.0 + 0.47 * 0.5 * time_e,
		"overshoot": clampf(0.344 - 0.458 * flow, 0.0, 1.0),
		"anticipation": clampf(0.223 + 0.297 * weight, 0.0, 1.0),
		"torso_turn": clampf(0.29 - 0.331 * flow + 0.04 * weight, 0.05, 0.8),
		"look_often": clampf(1.078 - 1.225 * space, 0.2, 2.5),
		"look_far": clampf(1.21 - 0.804 * space, 0.3, 2.2),
		"breath": clampf(0.641 - 0.123 * weight, 0.3, 1.0),
		"rise": clampf(-(0.136 - 0.819 * weight), -1.0, 1.0),        # + rising (Light), - sinking (Strong)
		"spread": clampf(0.195 + 0.164 * weight - 0.365 * flow, -1.0, 1.0),
		# tension (Neff & Fiume): Bound -> stiff, well-damped springs; Free -> loose, swinging
		"stiff": clampf(1.0 + 0.45 * flow, 0.5, 1.6),
		"damp": clampf(0.55 + 0.2 * flow, 0.3, 0.9),
		# body and age (gait_reference.md)
		"stride": float(g[0]) * lerpf(1.0, 0.78, elder) * lerpf(1.0, 1.08, child),
		"cadence": float(g[1]) * lerpf(1.0, 0.92, elder) * lerpf(1.0, 1.25, child),
		"bounce": float(g[2]) * lerpf(1.0, 0.6, elder) * lerpf(1.0, 1.4, child),
		"arm_swing": float(g[3]) * lerpf(1.0, 0.6, elder),
		"knee_swing": lerpf(1.0, 0.75, elder),
		"base": lerpf(1.0, 1.8, maxf(elder, heavy * 0.8)) * lerpf(1.0, 1.4, child),
		"lean": lerpf(0.0, deg_to_rad(9.0), elder) + deg_to_rad(10.0) * clampf(-float(v.get("posture", 0.2)), 0.0, 1.0),
		"sway": 1.0 + 0.5 * heavy + (0.35 if v.get("sex", "") == "female" else 0.0),
		# mood (Roether et al. 2009)
		"head_down": 0.0, "elbow": 0.0, "amp": 1.0,
	}
	match mood:
		"sad":
			s.head_down = deg_to_rad(18.0)
			s.amp = 0.7
			s.speed *= 0.8
		"happy":
			s.amp = 1.25
			s.speed *= 1.1
			s.bounce *= 1.2
		"angry":
			s.amp = 1.25
			s.elbow = deg_to_rad(25.0)
			s.speed *= 1.15
		"afraid":
			s.amp = 0.75
			s.elbow = deg_to_rad(20.0)
			s.head_down = deg_to_rad(6.0)
	return s
