extends RefCounted
class_name NpcRng

## Deterministic randomness for generated people: every trait of every person draws from its own
## stream, seeded by fnv1a64("seed|person_id|trait_id") and run through splitmix64.  Adding a trait
## never disturbs another trait's numbers, any trait can be computed in any order on any thread,
## and the same person comes out identically every time -- the "noise-based RNG" idea (Eiserloh,
## GDC 2017).  Bit-for-bit the same as tools/charref/traits.py (Stream, fnv1a64), so the Python
## tool previews exactly the people the game makes; remake/tools/npc_parity.gd checks it.
##
## GDScript ints are signed 64-bit and wrap on overflow, which is exactly the unsigned arithmetic
## these hashes need; only the right shifts must be made logical (lsr).

const FNV_OFFSET := -3750763034362895579          # 0xcbf29ce484222325
const FNV_PRIME := 1099511628211                   # 0x100000001b3
const GOLDEN := -7046029254386353131               # 0x9E3779B97F4A7C15
const MIX1 := -4658895280553007687                 # 0xBF58476D1CE4E5B9
const MIX2 := -7723592293110705685                 # 0x94D049BB133111EB
const TWO53 := 9007199254740992.0

var s: int


func _init(seed: int = 0) -> void:
	s = seed


static func fnv1a64(text: String) -> int:
	var h := FNV_OFFSET
	for b in text.to_utf8_buffer():
		h = (h ^ b) * FNV_PRIME
	return h


static func for_trait(world_seed: int, person_id: String, trait_id: String) -> NpcRng:
	return NpcRng.new(fnv1a64("%d|%s|%s" % [world_seed, person_id, trait_id]))


static func lsr(x: int, n: int) -> int:
	return (x >> n) & ((1 << (64 - n)) - 1)


func u64() -> int:
	s += GOLDEN
	var z := s
	z = (z ^ lsr(z, 30)) * MIX1
	z = (z ^ lsr(z, 27)) * MIX2
	return z ^ lsr(z, 31)


func rand() -> float:
	## [0, 1)
	return float(lsr(u64(), 11)) / TWO53


func normal(mu := 0.0, sd := 1.0) -> float:
	var u := maxf(rand(), 1e-12)
	return mu + sd * sqrt(-2.0 * log(u)) * cos(2.0 * PI * rand())


func gamma(k: float) -> float:
	## Marsaglia-Tsang; k < 1 boosted.  Same draw order as the Python tool.
	if k < 1.0:
		var g := gamma(k + 1.0)
		return g * pow(rand(), 1.0 / k)
	var d := k - 1.0 / 3.0
	var c := 1.0 / sqrt(9.0 * d)
	while true:
		var x := normal()
		var v := pow(1.0 + c * x, 3.0)
		if v > 0.0 and log(maxf(rand(), 1e-12)) < 0.5 * x * x + d - d * v + d * log(v):
			return d * v
	return d


func pick(weights: Dictionary) -> Variant:
	var tot := 0.0
	for k in weights:
		tot += maxf(0.0, float(weights[k]))
	var r := rand() * tot
	for k in weights:
		r -= maxf(0.0, float(weights[k]))
		if r < 0.0:
			return k
	return weights.keys()[-1]
