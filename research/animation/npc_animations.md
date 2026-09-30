# The NPC animation list: what townsfolk need, and how each should look

This covers what the townspeople of Space Station Columbia need in order to live convincingly,
and how each animation should look. It draws on RAGE's townsfolk and enemies, TLOU2's systemic
NPCs, the craft principles (`principles.md`), personality and emotion in motion
(`expressive_motion.md`) and our Ghibli direction ("the spectacular mundane": people shown at
their daily work, `../characters/ghibli_style.md`).

**Legend.** *Layer:* **P** procedural, done by NpcAnimator's layers, no clip; **C** authored clip
(npc_clips.json); **S** smart object or action station (the place supplies position, props and
clip). *Status:* ✅ built · 🟡 partly built · ⬜ to do. Every clip is scaled by personality
(PERFORM: Sudden people quicker, Free people overshoot, Strong people anticipate more) and by
mood (Roether), and plays over planted feet and the spring layer.

## 1. The rig (61 bones)
The layout follows the standard game humanoids (Unity Humanoid, the Unreal mannequin):

| group | bones | why |
|---|---|---|
| spine and head | Hips, Spine, Chest, **UpperChest**, Neck, Head, **Jaw** | a three-part spine for curves, breath and slumps; the jaw drops the chin in speech and laughter |
| each arm | Shoulder (clavicle), UpperArm, **UpperArmTwist**, LowerArm, **LowerArmTwist**, Hand, **Prop** | twist bones stop the forearm collapsing when the wrist turns (the "candy wrapper"); the prop socket holds cups, tools, bags and umbrellas |
| each leg | UpperLeg, LowerLeg, Foot, **Toe** | heel-to-toe roll, push-off, kneeling, tiptoe |
| each hand | Thumb, Index, Middle, Ring, Pinky × **3 segments** | real grips and gestures: pointing, pinching, holding, counting |
| secondary | HairA, HairB | swinging ponytails, braids and long hair |

Eyes, lids, brows and the mouth shape are drawn by the face shader and animated as parameters
(gaze, blink, brow height, mouth open, smile).

## 2. Principles every NPC animation follows
1. **A home pose** per person (RAGE's Mayor): from occupation and personality (hands clasped, behind the
   back, arms folded, a hand on the hip, lapels, braced on a counter). Gestures leave from it and
   return to it.
2. **Asymmetry:** no twins. One hand acts and the other rests; the weight sits on one leg; the head
   tilts.
3. **Tame, stroke, hold, return:** a slow build, a snap into the key pose, a readable hold (0.8–1.6 s
   at a gesture's extreme), a softer return.
4. **Weight:** squash on landing, sitting and lifting; settle after stopping; the body leans into
   loads.
5. **Eyes lead, head follows, body last** on every turn and look.
6. **Interruptible** at any frame; reactions by cause.
7. **Economy:** a seated or leaning person acts with the head and one hand (Ginny, Coffer).
8. **Ma:** long still holds are part of the performance.

## 3. The list

### 3.1 Locomotion
| animation | layer | how it should look | status |
|---|---|---|---|
| walk | P | feet planted and heel-to-toe; narrow step line; pelvis bob, shift, list and rotation; counter-rotating chest; arms swinging slightly across; level head | ✅ |
| walk, styles by personality, mood and age | P | stride, cadence, bounce and arm swing from gait; sad heads down; elders shorter steps, wider base and leaning; children bouncy | ✅ |
| start / stop | P | a rock back (tame) before the first step; the lean carries on past a stop and settles | ✅ |
| turn while walking | P | eyes, then head, then shoulders, then hips over ~0.5 s | ✅ |
| turn on the spot | C | eyes and head first; small steps (two or three) round; weight transfer | ⬜ |
| jog / run | P | flight phase; forward lean; arms bent ~90°; for hurrying, rain and children | ⬜ |
| stairs and slopes | P | per-foot ground height; lean into climbs; shorter steps down | ⬜ |
| stop and look (curiosity) | C | slow, head forward, a slight lean, a hand half raised | ⬜ |
| walk carrying (bag, basket, box, bucket) | P+C | the load arm straight, the shoulder dropped on its side, the body leaning away; two-handed boxes held at the belly with the back arched | ⬜ |
| walk with a cane or walker | P+C | the cane planted with the opposite foot; a slower, three-point rhythm | ⬜ |
| stroll with hands behind the back | P | the stance held while walking; slower | ⬜ |

### 3.2 Standing idle (home poses and variations)
| animation | layer | how it should look | status |
|---|---|---|---|
| neutral, contrapposto, weight shifts | P | weight on one leg, the other knee eased; a shift every 6–24 s | ✅ |
| breathing | P | upper chest rises; slower for calm, Light people | ✅ |
| hands clasped front / behind back / arms folded / hand on hip | P | stances by personality, by arm IK | ✅ |
| thumbs in pockets / lapels | C | thumbs hooked, chest out (Mayor Clayton); for extraverted, dominant people | ✅ (lapels) |
| look around (glance), blink | P | eyes lead; blinks with gaze shifts, 15–20 a minute | ✅ |
| check the time (watch) | C | the wrist raised and turned in, the head down to it, a short hold, a small "hm" | ✅ |
| stretch | C | arms up and back (tame), a hold with the chest lifted, drop and shake out | ✅ |
| yawn | C | a hand to the mouth, the head back, the jaw open, eyes shut | ✅ |
| scratch head / neck | C | a hand to the back of the head, two or three small strokes, the head tilted | ✅ |
| rub hands (cold) | C | hands together in front, rubbing, shoulders up | ✅ |
| rub neck / back (tired) | C | a hand to the lower back, arching back, a wince | ✅ |
| shift from foot to foot (impatient) | P | faster weight shifts, a foot tap | ⬜ |
| tap foot | C | the toe raised and tapped in rhythm | ⬜ |
| wipe brow (heat, work) | C | the back of the wrist across the forehead, a breath out | ✅ |
| fix hat / hair | C | a hand to the brim or hair, a small adjust | ✅ |
| brush off clothes | C | two brushes at the thigh or chest, a look down | ✅ |

### 3.3 Social: conversation and greeting
| animation | layer | how it should look | status |
|---|---|---|---|
| talk: beat gestures | P | Kendon phases, faster and bigger for extraverts, nods on the beats | ✅ |
| explain (open palm) | C | a palm up at the chest, out a little; a hold | ✅ |
| offer / present | C | a palm up swept out to the side (the Mayor) | ✅ |
| point (deictic) | C | index extended, arm toward the target, head and eyes there first | ✅ |
| wave hello / goodbye | C | the forearm up, a relaxed palm out, 2–3 side-to-side waves from the elbow, drop | ✅ |
| nod yes / shake no | C | 2–3 nods, decreasing; shakes with a slight shoulder turn | ✅ |
| shrug | C | shoulders up, palms up and out, the head tilted, brows up; a hold; drop | ✅ |
| laugh | C | the head back, then forward on each "ha"; shoulders bouncing; a hand to the belly; eyes shut, mouth open, smile | ✅ |
| listen / think | C | a hand to the chin, the head tilted, eyes up and aside, a slow nod | ✅ |
| hands up "whoa / wait" | C | palms out at the chest, a small step back | ✅ |
| bow / head dip (polite) | C | a small forward bend at the upper spine, the head lower, a hold | ✅ |
| cross arms (disagree) | P/C | the folded stance, the head back a touch, weight back | ✅ (stance) |
| beckon ("come here") | C | palm up, fingers curling in twice | ✅ |
| hand on heart (sincere) | C | a hand flat on the chest, a small bow of the head | ✅ |
| facepalm (exasperated) | C | a hand to the forehead, the head dropping into it | ✅ |
| clap | C | 3–5 claps at chest height, then hands down | ✅ |
| handshake (with the player) | S | an arm out, grip, 2 pumps; needs the player's hand | ⬜ |
| two NPCs chatting | S | face each other at ~1.2 m, turn-taking gestures, listen and nod | ⬜ |

### 3.4 Reactions
| animation | layer | how it should look | status |
|---|---|---|---|
| startle (a sudden noise, the player too close) | C | a flinch: shoulders up, arms in, a half step back, then a settle and a stare | ✅ |
| surprised "oh!" | C | brows up, the head back, a hand to the chest | ✅ |
| step back (personal space) | C | a small step back, the head back | ⬜ |
| look at the player as they pass | P | the head turns to track, the eyes first; for curious people | ⬜ |
| cower / protect (danger) | C | arms over the head, a crouch, turned away | ✅ |
| flinch at a hit (bump, shove) | C+P | a hit-location reaction (RAGE): clutch the spot, stagger a step | ⬜ |
| stumble / trip | C | a foot catches, arms out, a quick recovery step | ⬜ |
| fall and get up | C | a ragdoll-like fall into a key pose; up via knee and hand | ⬜ |
| cold shiver | C | shoulders up, arms hugged, a quick tremor | ✅ |
| rain: hunch, hand over the head | C | shoulders up, the head down, a hand held over the head, hurrying | ✅ |
| sneeze / cough | C | a tame build (inhale, head back), a sudden snap forward, a hand to the mouth | ✅ |

### 3.5 Sitting, leaning, lying (smart objects)
| animation | layer | how it should look | status |
|---|---|---|---|
| sit down on a bench or chair | S+C | a look back at the seat, a hand toward it, the hips back and down with the knees, a settle | ✅ |
| seated idle | C | forearms on the thighs or hands in the lap; acting by the head and one hand (Ginny) | ✅ |
| seated, cross legs / lean back | C | one leg over; an arm along the bench back | ⬜ |
| stand up from sitting | S+C | lean forward (the nose over the toes), hands push on the knees, rise | ✅ |
| sit on the ground / steps | S+C | lower via a knee, legs out or crossed | ⬜ |
| lean on a wall | S+C | shoulder or back to the wall, one foot up flat against it, arms folded | ⬜ |
| lean on a counter / railing | S+C | forearms on it, shoulders hunched, weight on one leg (Coffer) | ✅ |
| crouch and look / pick up | C | squat, knees apart, forearms on the knees; or pick up and stand | ✅ |
| kneel (garden, pray) | C | down on one knee, then both | ⬜ |
| lie on the grass | S | on the back, hands behind the head | ⬜ |

### 3.6 Work by occupation (the spectacular mundane)
| occupation | clips | how they should look | status |
|---|---|---|---|
| shopkeeper / clerk | wipe counter, count coins, write in a ledger, lean on the counter | circular wiping from the shoulder; the head down to the ledger | 🟡 (lean, wipe) |
| baker / cook | knead dough, stir a pot, carry a tray | kneading as a rocking push from the hips, the heels of both hands | ✅ (knead, stir) |
| farmer | hoe, dig, carry a sack on the shoulder, feed animals | the hoe raised, weight into the downstroke, a pause and a wipe of the brow | ✅ (hoe) |
| fisher / dock worker | haul a rope hand over hand, coil a rope, mend a net | hand over hand with the whole back, legs braced | ✅ (haul) |
| builder / mechanic | hammer, saw, carry planks, look under a hood | the hammer: a raise (tame), a strike (tsume), a small rebound, a look | ✅ (hammer) |
| sweeper / homemaker | sweep, hang washing, beat a rug | sweeping in arcs from the hips, stepping back; stretch up to the line | ✅ (sweep) |
| waiter / server | carry a tray at the shoulder, wipe a table, take an order (write) | the tray level; hips lead through turns | ⬜ |
| teacher / clerk | read a paper, write on a clipboard | the head down, a page turn with a flick | ✅ (read) |
| police / postal | patrol with hands behind the back, hand over a letter, salute | upright, a slow stroll; a crisp salute (tsume) | ✅ (salute) |
| nurse / doctor | check a clipboard, walk briskly | brisk, upright | ⬜ |
| retired | sit on a bench, feed birds, lean on a cane, doze | slow; long holds; the head nodding off and jerking up | 🟡 (doze) |
| children | play: skip, run in circles, crouch at something, throw a ball | bouncy, quick, big arcs; the head leads | ⬜ |

### 3.7 Everyday actions with props
| animation | layer | how it should look | status |
|---|---|---|---|
| drink from a cup / bottle | C | the cup up in an arc, the head tilts back, a hold, down; a breath after | ✅ |
| eat (sandwich, apple) | C | a bite: the head forward to meet the hand, chewing on the jaw | ✅ |
| read a newspaper | C | both hands out, the head down; a page turn | ✅ |
| use the PDA (communicator) | C | held in both hands at the chest, the head down, thumbs tapping | ✅ |
| smoke / pipe | C | the hand to the mouth, a hold, out, exhale with the head back | ⬜ (setting choice) |
| open umbrella / hold it | C+P | open overhead, the arm held up, the elbow bent | ⬜ |
| open / close a door | S | reach, pull or push with the body behind it, step through | ⬜ |
| knock on a door | C | 2–3 knocks from the wrist, a step back, wait | ✅ |
| pick up / put down | C | squat (not bend) for heavy things; bend for light ones; a look first | ✅ (pick up) |
| hand over / receive (to the player) | C | an arm out, a hold until taken, the hand back | ✅ (offer) |
| carry a box / bucket | P+C | see locomotion | ⬜ |

### 3.8 Emotional states (layered over everything)
| state | how it should look | status |
|---|---|---|
| happy | larger movement, faster, more bounce; a smile | ✅ (mood) |
| sad | the head down, smaller and slower movement, slumped chest | ✅ (mood) |
| angry | faster, bigger, elbows bent, fists | ✅ (mood) + clip ⬜ (fist shake) |
| afraid | smaller, elbows in, upper arms back, knees bent, glancing | ✅ (mood) |
| tired | slow, heavy steps, shoulders down, yawns, rubbing the neck | 🟡 (clips) |
| nervous | fidgeting, frequent glances, touching the face or hair, shifting weight | ⬜ |
| bored | slow looks, sighs, leaning, tapping | ⬜ |

## 4. What's built now
- **Clip library.** `godot_project/remake/characters/npc_clips.json` holds 51 clips: every ✅ clip
  above.
  - Each clip is a list of key poses, in body-relative terms: hand targets in the upper-chest,
    hips, head or root frame; elbow poles; wrist angles; grips; spine and head angles (+pitch is
    forward); clavicle raises (`shoulders`); hips and feet for full-body moves; and the face.
  - **Keys are poses:** a channel a key leaves out holds its last value, so `{"t", "w"}` alone is
    a hold. Easing is tame or tsume.
  - A hand moving between frames (chest to mouth) is blended in skeleton space.
  - NpcAnimator plays each clip over the procedural layers, adding the cartoon filter's
    anticipation and follow-through, personality-scaled timing, and blend in and out.
- **Props** (`npc_props.gd`): cup, apple, paper, PDA, spoon, hammer, broom and hoe sit on the
  PropL/PropR sockets. Long tools (broom, hoe) are aimed every frame from the upper hand through
  the lower one.
- **Behaviour.**
  - **Ambient idles:** standing people break into idles every 14–44 s. Extraverts fidget more
    often. The `ambient` table in the JSON is weighted by age: elders rub their backs, children
    crouch and look.
  - **Greetings:** on contact the NPC greets by personality. Warm extraverts wave, very warm
    people may put a hand on their heart, and everyone else nods. Then the talk beats start.
  - **Interruptible:** walking off cuts a clip short.
- **Checks.**
  - The lineup tool's `clip` view renders a clip as a strip of moments, left to right
    (`NPC_CLIP=wave`).
  - `remake/tools/npc_clip_test.gd` plays every clip on 12 varied bodies and checks every bone
    stays finite and every clip ends: 51 × 12, 52,032 frames, 0 failures.
- **Not yet.** Home poses are wired only as clips (`lapels`, `lean_counter`, `sit_idle`). Choosing
  them per person, and the counters and benches they need, wait for smart objects (§5).

## 5. Next
- two-person scenes (chats, handshakes);
- smart objects in the world (benches, counters, walls, doors) with action-station entry and exit;
- run, stairs and slopes; carrying loads while walking;
- hit reactions and falls, with a physical response blended back in (Zordan 2005);
- children's play;
- work routines tied to occupation and schedule.
