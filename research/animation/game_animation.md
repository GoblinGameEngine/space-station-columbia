# Animating characters in 3D games: what the best do, studied frame by frame

This is the practice of acclaimed game character animation, above all id Software's **RAGE** (2011),
studied from footage, and the literature on animating characters for games. It complements the
craft and procedural research in this folder. Footage is local and gitignored, in
`reference/animation/games/` (and `study/` holds the contact sheets and strips made from it).

## 1. RAGE (id Software, 2011)
**Why it is famous.** Reviews singled out its character animation:
- enemies dodge and flip, climb walls and ceilings, and launch themselves off objects;
- every bullet that connects gets a reaction: clutching the wound, limping after a leg shot,
  stumbling, a last attempt from a mangled body;
- each clan moves differently: the Ghost Clan is acrobatic, the Shrouded Clan armoured and
  cover-seeking, the Wasted Clan all personality.

id's Matt Hooper described "surprising amounts of expressive hand-keyed animation": "the
different characters look so wild and out there that it almost demands that over-the-top
animation treatment" (*Game Developer*, "Technology, Design: RAGE").

**Scale, in id's own words** (the "Dev Diary: The Enemies" / "Making Of the Enemy" videos, transcribed):
- "upwards of **6,000 animations**"; "one type of character may have **300, 400, 500
  animations**";
- motion capture as the base, with hand-keyed exaggeration on top;
- **the animation state follows the AI state.** When shot, enemies "freak out", go into a
  "scramble mode" running to save their lives, then dive into cover, "not really scripted";
- **animations are interruptible**: "it's not like they're just stuck in that particular
  animation";
- **personality in the fighting style**: "if you add personality to the fighting skills and add
  personality to the characters it really makes the world more refreshing."

**Frame by frame: a mutant charge** (`study/best_frames_a.jpg`, 30 fps):
- the mutant runs the length of a pipe in a **wide, asymmetric silhouette**, arms flung out
  differently, never a mirrored "twin" pose;
- the spacing shows acceleration, with drawings bunched at the start;
- **landing squashes it low** (knees and hips down, head forward) for a few frames before it
  drives on: weight made visible;
- a hit gives an instant, location-specific flinch.

**Frame by frame: the townsfolk of Wellspring** (`study/mayor_strip.jpg`,
`study/three_strips.jpg`, 25 fps sampled every 0.4 s):
- **Mayor Clayton** has a **character "home pose"**: both thumbs hooked in his lapels, chest
  out, leaning back a touch (pride, self-importance).
  - Every gesture leaves the home pose and returns to it, and the gestures are **asymmetric**:
    one hand stays on the lapel while the other acts (a palm-up offer swept out to the side, an
    open-palm "here's how it is" at the chest, a raised palm-out "hold on").
  - Timing: out in ~0.4–0.8 s, **held 0.8–1.6 s**, back in ~0.4 s, then a rest in the home pose.
  - The head is never dead: tilts, turns, nods, with small hip rocks and weight shifts.
- **Ginny** sits on a crate, leaning forward with her forearms on her knees and a bottle beside
  her. Her acting is almost all **head** (tracking the player, nods and tilts on her lines) and
  **one hand** lifting off the knee palm-up and settling back. The legs don't move. Seated acting
  is economical.
- **Coffer**, the vendor, leans over his counter, shoulders hunched and forearms braced on it.
  **The job's posture is the home pose.** A hand leaves the counter to gesture and comes back.
- **Sally**, the bartender, stands with a hand on her hip, weight on one leg (contrapposto), head
  cocked.

**What we take from RAGE**
1. **Every character has a home pose** (from occupation and personality) that gestures leave and
   return to.
2. **Asymmetry** everywhere: hands, weight, head tilt.
3. **Holds** (0.8–1.6 s) at the extremes of a gesture: the pose reads.
4. **Weight shown on contact**: squash on landing, dip on sitting, settle after stopping.
5. **Reactions are specific** (where you were hit, what startled you) and animation follows the
   AI state.
6. **Everything interruptible.**
7. **Volume.** Hundreds of animations per character type. Procedural variation multiplies what
   we author.

## 2. Others at the top
- **The Last of Us Part II** (Naughty Dog, 2020; the "Animation and AI Gameplay System
  Breakdowns" video, `study/ov_Lsu02AEw72Q.jpg`): interactions begin with a **15-frame
  (0.5 s) align/warp** to an anchor, then play an authored clip of 60–600 frames. NPCs **move to
  anchors, "enter action stations"** with a blend and exit with their own clip. Opt-in
  conversations and "NPC gatekeeping" hold NPCs at points until the player arrives. GDC 2021
  talks: "Bringing Allies to Life" and "Emotional Systemic Facial". NPC animation was led by
  Michal Mach.
- **Red Dead Redemption 2** (Rockstar): about **300,000 animations**. NPCs eat, drink and react to
  weather and to the player; GTA VI reportedly doubles that.
- **DOOM (2016)** (id): "push-forward combat"; glory kills are context-sensitive animations
  kept to hundreds of milliseconds so the player keeps moving (Kurt Loudy & Jake Campbell, GDC
  2018).
- **Half-Life 2** (Valve): citizens with scripted "choreography" scenes and ambient acting.

## 3. The literature
- **Jonathan Cooper, *Game Anim: Video Game Animation Explained*** (CRC 2019; 2nd ed. 2021):
  the twelve principles reinterpreted, plus **five fundamentals of game animation**:
  - **Feel:** response, inertia and momentum, visual feedback;
  - **Fluidity:** blending and transitions, seamless cycles, settling;
  - **Readability:** posing for game cameras, silhouettes, collision, centre of mass and balance;
  - **Context:** how the animation serves the story and the character, their quirks;
  - **Elegance:** an efficient animation system.
- **Jason Gregory, *Game Engine Architecture*** (ch. "Animation Systems"): skeletal animation,
  blend trees, additive and partial-skeleton layers, IK, the action state machine.
- **Kallmann & Thalmann, "Modeling Objects for Interaction Tasks"** (Computer Animation 1999)
  and "Smart Objects": objects carry the information on how to interact with them (grasp
  sites, positions, parts, scripts). That is what TLOU2's anchors and action stations are. For us:
  benches, counters, doorways and wells know where to stand and which clip to play.
- **Zordan, Majkowska, Chiu & Fast, "Dynamic Response for Motion Capture Animation"**
  (SIGGRAPH 2005): a physical response to impacts, then a search for the best clip to re-enter.
  This is how reactions blend back into animation.
- **Hoyet, McDonnell & O'Sullivan, "Push It Real: Perceiving Causality in Virtual Interactions"**
  (SIGGRAPH 2012): how viewers judge whether reactions look caused by an impact.
- **Bereznyak, "IK Rig: Procedural Pose Animation"** (Ubisoft, GDC 2016): one animation retargeted
  at runtime to any body and adapted to props, terrain and state (tired, wounded). This is the
  principle behind our body-relative clips.
- **Laurent Delayen, Paragon locomotion** (Epic, 2016): distance matching, orientation and speed
  warping, so starts and stops land exactly with no foot sliding.
- **Unity Humanoid / Unreal mannequin conventions:** the standard game humanoid has 15 required
  bones; optional upper chest, jaw, eyes, toes and 3-segment fingers; twist bones against the
  candy-wrapper collapse of linear skinning. UE4's mannequin has ~68 bones, UE5's 89.
- The classical and procedural sources in this folder: Thomas & Johnston, Lasseter, Williams,
  Laban/EMOTE/PERFORM, Perlin, Wang et al.'s cartoon filter, Johansen, Hecker.

## 4. Consequences for our generator
- **Rig:** 61 bones (npc_animations.md §1): a three-part spine, jaw, twist bones, 3-segment
  fingers, toes, prop sockets, hair chain.
- **Clips:** authored key poses in body-relative terms (IK Rig's lesson), easing by tame and tsume,
  holds at the extremes (RAGE), automatic anticipation and follow-through (the cartoon filter),
  personality-scaled timing (PERFORM), over the procedural layers (planted feet, springs).
- **Home poses** per person (RAGE): from occupation and personality.
- **Smart objects / action stations** (Kallmann; TLOU2): places that tell an NPC where to stand
  and what to play, entered with a 0.5 s align and left with an exit clip.
- **Interruptible by design**, **reactions by cause**, **variety by composition** (base clip ×
  personality timing × body × mood × prop).
