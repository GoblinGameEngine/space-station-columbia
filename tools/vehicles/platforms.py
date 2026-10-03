#!/usr/bin/env python3
"""The boards: the vehicle platforms (skateboard chassis) every ground vehicle is built on -- engineering
data for the game and for the chassis builds.

    python3 tools/vehicles/platforms.py      # -> godot_project/remake/vehicles/chassis/platforms.json

Canon (the user, 2026-10-01; tools/bible/canon_industry.py): the Steward makes one board, pattern
HMP-1, unchanged since the launch, sleek, organic and spare of material, for the heavy vehicles; the
three vehicle works make their own cruder boards -- tube frames carrying their motors, batteries and
electronics -- for personal and passenger vehicles. Every board keeps the Pattern, so any body fits
any board of its width.

The research behind the numbers: research/vehicles/skateboard_chassis.md.

Each board is a list of discrete modules (the unit of interchange and of destruction): id, kind,
position (x right, y forward, z up, metres; y = 0 midway between the outer axles; z = 0 the ground),
size (the module's box: its collider, and the builders' envelope), mass_kg, hp (hit points: what it
takes to break it off or kill it), attach (the module it hangs from; None = the root), and kind data.
The chassis builder (remake/blender/chassis/chassis.py) gives each module its shape, by family.
"""
import json
import os

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
OUT = os.path.join(ROOT, "godot_project", "remake", "vehicles", "chassis", "platforms.json")

# ---------------------------------------------------------------- the Pattern (the body interface)
PATTERN = {
    "deck_top_m": 0.50,          # the mounting face, above the ground (laden, at rest)
    "mount_pitch_m": 0.75,       # body mounts every 0.75 m along each side rail
    # the mount rails' half-spacing by width class: inboard of the wheels (the deck sits between them,
    # like a skateboard's), so a body's arches clear the tyres and any body fits any board of its class
    "mount_x_m": {"narrow": 0.50, "standard": 0.60, "broad": 0.70, "heavy": 0.80, "farm": 0.55, "rail": 0.55},
    "socket": "behind the front axle on the centre line: power (the pack's bus) and control (the drive command, by wire)",
}

# ---------------------------------------------------------------- the Steward's board, pattern HMP-1
# one printed span of deck: a bone-like lattice of Spindle alloy with the sealed cells set in it
STEWARD_CLASS = {
    #           track  deck_w  wheel_r  deck_thick  span_kg  span_kwh  pod_kg  pod_kw  pod_nm   hp_span hp_pod
    "narrow": (1.50, 1.20, 0.31, 0.15, 40.0, 8.0, 45.0, 40.0, 900.0, 900, 700),
    "broad": (1.95, 1.60, 0.40, 0.19, 62.0, 12.0, 80.0, 90.0, 2200.0, 1300, 1000),
    "heavy": (2.20, 1.80, 0.48, 0.23, 95.0, 18.0, 130.0, 160.0, 5200.0, 2000, 1500),
    # the farm board (2026-10-02): a narrow deck between big equal wheels -- the Steward's tractors
    "farm": (2.00, 1.30, 0.62, 0.19, 62.0, 12.0, 110.0, 90.0, 4500.0, 1300, 1100),
    # the rail board (2026-10-02): standard gauge (1,435 mm), two-axle bogies, a deck between them
    "rail": (1.435, 2.20, 0.46, 0.23, 95.0, 18.0, 130.0, 160.0, 5200.0, 2000, 1500),
}
SPAN = 0.75                      # the span pitch (= the Pattern's mount pitch)
CAP = 0.35                       # the nose and tail caps


def steward(id_, cls, spans, axle_spans, steer_axles):
    """A Steward board of `spans` spans, axles at the given span joints (0 = the front cap's joint)."""
    track, width, r, thick, span_kg, span_kwh, pod_kg, pod_kw, pod_nm, hp_span, hp_pod = STEWARD_CLASS[cls]
    length = spans * SPAN + 2 * CAP
    y_front = length / 2 - CAP                     # the first joint
    z_top = PATTERN["deck_top_m"]
    z_mid = z_top - thick / 2
    mods = [dict(id="cap_front", kind="steward_cap", pos=[0, y_front + CAP / 2, z_mid], size=[width, CAP, thick], mass_kg=round(span_kg * 0.2, 1), hp=hp_span // 2, attach="span_0", end="front")]
    for i in range(spans):
        y = y_front - (i + 0.5) * SPAN
        mods.append(dict(id="span_%d" % i, kind="steward_span", pos=[0, round(y, 3), z_mid], size=[width, SPAN, thick], mass_kg=span_kg, hp=hp_span,
                         attach=None if i == 0 else "span_%d" % (i - 1), kwh=span_kwh, cells="sealed"))
    mods.append(dict(id="cap_rear", kind="steward_cap", pos=[0, -(y_front + CAP / 2), z_mid], size=[width, CAP, thick], mass_kg=round(span_kg * 0.2, 1), hp=hp_span // 2,
                     attach="span_%d" % (spans - 1), end="rear"))
    axles = []
    for ai, j in enumerate(axle_spans):
        y = y_front - j * SPAN
        tag = "F" if ai == 0 else ("B" if ai == len(axle_spans) - 1 else "M%d" % ai)
        axles.append(dict(tag=tag, y=round(y, 3), steer=ai in steer_axles, driven=True))
        host = "span_%d" % min(max(j - 1, 0), spans - 1) if j > 0 else "span_0"
        for side, sx in (("L", -1), ("R", 1)):
            mods.append(dict(id="pod_%s%s" % (tag, side), kind="steward_pod", pos=[sx * track / 2, round(y, 3), r], size=[0.42 + r * 0.6, r * 2.3, r * 2.2],
                             mass_kg=pod_kg, hp=hp_pod, attach=host, side=side, wheel="wheel_%s%s" % (tag, side), wheel_r=r, steer=ai in steer_axles,
                             motor="axial-flux, %g kW, %g Nm at the wheel" % (pod_kw, pod_nm), kw=pod_kw, nm=pod_nm,
                             has=["motor", "reduction", "steer-by-wire (+-35 deg)", "brake-by-wire", "active suspension", "the pod's own controller"]))
    mods.append(dict(id="socket", kind="pattern_socket", pos=[0, round(axles[0]["y"] - 0.4, 3), z_top], size=[0.24, 0.16, 0.03], mass_kg=1.5, hp=200, attach="span_0"))
    tyre_w = 0.24 if r < 0.35 else 0.32
    return dict(id=id_, name="Steward board, pattern HMP-1, %s, %d spans" % (cls, spans), maker="steward", family="steward", board="steward_board", cls=cls,
                length_m=round(length, 3), deck_width_m=width, width_m=round(track + tyre_w + 0.06, 3), mount_x_m=PATTERN["mount_x_m"][cls], track_m=track, wheel_r=r, wheelbase_m=round(axles[0]["y"] - axles[-1]["y"], 3), axles=axles,
                drive="every wheel (a motor in each pod)", steering="by wire; %d of %d axles" % (len(steer_axles), len(axles)),
                pack_kwh=round(span_kwh * spans, 1), power_kw=round(pod_kw * 2 * len(axles)), modules=mods)


# ---------------------------------------------------------------- people's boards: the three works
def mounts(cls, length, z_top):
    """The Pattern's mount rails: every human board carries them at the Steward's positions."""
    x = PATTERN["mount_x_m"][cls]
    return [dict(id="mount_rail_%s" % s, kind="mount_rail", pos=[sx * x, 0, z_top - 0.02], size=[0.06, length - 0.3, 0.04], mass_kg=round(4.5 * length / 4, 1), hp=300,
                 attach=None, holes_every_m=PATTERN["mount_pitch_m"]) for s, sx in (("L", -1), ("R", 1))]


def wheels(axles, track, r, tyre_kg, hp=250):
    out = []
    for a in axles:
        for side, sx in (("L", -1), ("R", 1)):
            out.append(dict(id="wheel_%s%s" % (a["tag"], side), kind="wheel", pos=[sx * track / 2, a["y"], r], size=[0.2, r * 2, r * 2], mass_kg=tyre_kg, hp=hp,
                            attach="corner_%s%s" % (a["tag"], side), steer=a["steer"], wheel_r=r))
    return out


def harrow(id_, wb):
    """The Harrow Ladder: two boxed rails, crates between them, one motor and a De Dion tube on leaf springs."""
    W, track, r = 1.80, 1.55, 0.32
    L = wb + 1.55
    yf, yb = wb / 2, -wb / 2
    zt = PATTERN["deck_top_m"]
    axles = [dict(tag="F", y=yf, steer=True, driven=False), dict(tag="B", y=yb, steer=False, driven=True)]
    rail_x = 0.52
    mods = [dict(id="rail_%s" % s, kind="harrow_rail", pos=[sx * rail_x, 0, 0.36], size=[0.075, L - 0.1, 0.15], mass_kg=round(14.5 * L, 1), hp=900, attach=None if s == "L" else "cross_0",
                 tube="150 x 75 x 4 mm boxed steel, rolled and seam-welded") for s, sx in (("L", -1), ("R", 1))]
    n_cross = 5
    for i in range(n_cross):
        y = yf + 0.55 - i * (wb + 1.1) / (n_cross - 1)
        mods.append(dict(id="cross_%d" % i, kind="harrow_cross", pos=[0, round(y, 3), 0.36], size=[rail_x * 2, 0.06, 0.10], mass_kg=9.0, hp=500, attach="rail_L"))
    for i in range(6):                                  # outriggers carrying the mount rails
        y = yf + 0.3 - i * (wb + 0.6) / 5
        for s, sx in (("L", -1), ("R", 1)):
            mods.append(dict(id="outrigger_%d%s" % (i, s), kind="harrow_outrigger", pos=[sx * (rail_x + 0.06), round(y, 3), 0.44], size=[0.14, 0.05, 0.10],
                             mass_kg=2.5, hp=200, attach="rail_%s" % s))
    mods += mounts("standard", L, zt)
    for i in range(4):
        y = yf - 0.55 - i * 0.5
        mods.append(dict(id="crate_%d" % i, kind="harrow_crate", pos=[0, round(y, 3), 0.33], size=[0.92, 0.40, 0.24], mass_kg=62.0, hp=350, attach="rail_L",
                         kwh=7.5, cells="LFP prismatic, steel cans, hand-built"))
    mods += [dict(id="motor", kind="harrow_motor", pos=[0, round(yb + 0.62, 3), 0.33], size=[0.34, 0.42, 0.34], mass_kg=85.0, hp=500, attach="cross_3",
                  motor="wound-rotor induction, 60 kW, 240 Nm, single reduction 9:1", kw=60.0, nm=240.0),
             dict(id="diff", kind="harrow_diff", pos=[0, round(yb + 0.18, 3), r], size=[0.36, 0.30, 0.30], mass_kg=32.0, hp=450, attach="cross_4"),
             dict(id="dedion", kind="harrow_dedion", pos=[0, round(yb - 0.08, 3), r], size=[track - 0.15, 0.10, 0.10], mass_kg=23.0, hp=500, attach="leaf_L"),
             dict(id="controller", kind="controller", pos=[0, round(yf - 0.32, 3), 0.40], size=[0.36, 0.22, 0.14], mass_kg=12.0, hp=120, attach="cross_1",
                  brains="two Thirty-Twos; contactors; a fan", heat="finned steel box")]
    for s, sx in (("L", -1), ("R", 1)):
        mods.append(dict(id="leaf_%s" % s, kind="harrow_leaf", pos=[sx * rail_x, round(yb, 3), 0.27], size=[0.07, 1.2, 0.12], mass_kg=18.0, hp=400, attach="rail_%s" % s,
                         spring="semi-elliptic, 7 leaves"))
        mods.append(dict(id="corner_F%s" % s, kind="harrow_front_corner", pos=[sx * (track / 2 - 0.2), round(yf, 3), r], size=[0.42, 0.36, 0.40], mass_kg=22.0, hp=350,
                         attach="rail_%s" % s, suspension="double wishbones, coil spring, lever damper; drum brake"))
        mods.append(dict(id="corner_B%s" % s, kind="harrow_hub", pos=[sx * (track / 2 - 0.12), round(yb, 3), r], size=[0.16, 0.3, 0.3], mass_kg=9.0, hp=300,
                         attach="dedion", suspension="De Dion tube, drum brake"))
    mods += wheels(axles, track, r, 18.0)
    return dict(id=id_, name="Harrow Ladder H-%d" % round(wb * 10), deck_width_m=PATTERN["mount_x_m"]["standard"] * 2 + 0.1, mount_x_m=PATTERN["mount_x_m"]["standard"], maker="harrow_motor_works", family="harrow", board="harrow_ladder", cls="standard",
                length_m=round(L, 3), width_m=W, track_m=track, wheel_r=r, wheelbase_m=wb, axles=axles, drive="rear (one motor, a differential, a De Dion tube)",
                steering="rack and pinion, mechanical", pack_kwh=30.0, power_kw=60.0, modules=mods)


def carrow(id_, wb):
    """The Carrow Keel: the pack in a central keel tube, a perimeter hoop (the gunwale), ribs, a motor per axle."""
    W, track, r = 1.80, 1.56, 0.32
    L = wb + 1.6
    yf, yb = wb / 2, -wb / 2
    zt = PATTERN["deck_top_m"]
    axles = [dict(tag="F", y=yf, steer=True, driven=True), dict(tag="B", y=yb, steer=False, driven=True)]
    keel_r = 0.17
    keel_l = wb - 0.5                                   # between the axles: the motors sit on the axle lines beyond its ends
    mods = [dict(id="keel", kind="carrow_keel", pos=[0, 0, 0.33], size=[keel_r * 2, keel_l, keel_r * 2], mass_kg=round(60 + 290, 1), hp=1400, attach=None,
                 tube="340 mm rolled steel tube, 3 mm (aluminium since VY 431)", kwh=36.0, cells="LFP cartridges, a string of 12, loaded from the hatch at the back"),
            dict(id="keel_hatch", kind="carrow_hatch", pos=[0, round(-keel_l / 2 - 0.04, 3), 0.33], size=[0.36, 0.08, 0.36], mass_kg=4.0, hp=150, attach="keel"),
            dict(id="gunwale", kind="carrow_gunwale", pos=[0, 0, zt - 0.03], size=[PATTERN["mount_x_m"]["standard"] * 2, L - 0.12, 0.06], mass_kg=30.0, hp=700, attach="keel",
                 tube="60 mm round steel tube, bent in one piece; it is the Pattern's mount rail")]
    for i in range(4):
        y = keel_l / 2 - 0.15 - i * (keel_l - 0.3) / 3
        for s, sx in (("L", -1), ("R", 1)):
            mods.append(dict(id="rib_%d%s" % (i, s), kind="carrow_rib", pos=[sx * 0.38, round(y, 3), 0.42], size=[0.44, 0.05, 0.16], mass_kg=3.0, hp=220, attach="keel"))
    for tag, y in (("F", yf), ("B", yb)):
        sy = 1 if tag == "F" else -1
        mods.append(dict(id="bulkhead_%s" % tag, kind="carrow_bulkhead", pos=[0, round(y + sy * 0.3, 3), 0.42], size=[PATTERN["mount_x_m"]["standard"] * 2, 0.06, 0.2],
                         mass_kg=7.0, hp=500, attach="keel", note="a cross tube from gunwale to gunwale, tied back to the keel's end: carries the motor and the suspension"))
        mods.append(dict(id="motor_%s" % tag, kind="carrow_motor", pos=[0, round(y, 3), r + 0.02], size=[0.30, 0.30, 0.30], mass_kg=55.0, hp=450,
                         attach="bulkhead_%s" % tag, motor="induction, 45 kW, 190 Nm, 8.5:1 with a differential", kw=45.0, nm=190.0))
        for s, sx in (("L", -1), ("R", 1)):
            mods.append(dict(id="corner_%s%s" % (tag, s), kind="carrow_corner", pos=[sx * (track / 2 - 0.22), round(y, 3), r], size=[0.46, 0.36, 0.44], mass_kg=20.0, hp=330,
                             attach="bulkhead_%s" % tag, suspension="double wishbones, coil-over damper; disc brake (front), drum (rear)", halfshaft=True))
                                                          # (the gunwale is the mount rail)
    mods.append(dict(id="controller", kind="controller", pos=[0, round(yf - 0.6, 3), 0.53], size=[0.32, 0.24, 0.10], mass_kg=12.0, hp=120, attach="keel",
                     brains="three Thirty-Twos: one per motor, one for the pack", heat="on the keel, cooled by it"))
    mods += wheels(axles, track, r, 17.0)
    return dict(id=id_, name="Carrow Keel K-%d" % round(wb * 10), deck_width_m=PATTERN["mount_x_m"]["standard"] * 2 + 0.1, mount_x_m=PATTERN["mount_x_m"]["standard"], maker="carrow_coach_company", family="carrow", board="carrow_keel", cls="standard",
                length_m=round(L, 3), width_m=W, track_m=track, wheel_r=r, wheelbase_m=wb, axles=axles, drive="both axles (a motor at each, inboard, with half-shafts)",
                steering="rack and pinion, mechanical", pack_kwh=36.0, power_kw=90.0, modules=mods)


def solana(id_, wb):
    """The Solana Lattice: lugged chromoly Warren-truss sides, side-loading battery cassettes, rear hub motors."""
    W, track, r = 1.76, 1.50, 0.30
    L = wb + 1.4
    yf, yb = wb / 2, -wb / 2
    zt = PATTERN["deck_top_m"]
    axles = [dict(tag="F", y=yf, steer=True, driven=False), dict(tag="B", y=yb, steer=False, driven=True)]
    x_top = PATTERN["mount_x_m"]["standard"]
    mods = []
    for s, sx in (("L", -1), ("R", 1)):
        mods.append(dict(id="truss_%s" % s, kind="solana_truss", pos=[sx * x_top, 0, 0.36], size=[0.14, L - 0.2, 0.28], mass_kg=22.0, hp=450,
                         attach=None if s == "L" else "cross_0", tube="32 and 25 mm drawn chromoly, brazed into lugs", panels=8))
    for i in range(7):
        y = yf + 0.55 - i * (wb + 1.1) / 6
        mods.append(dict(id="cross_%d" % i, kind="solana_cross", pos=[0, round(y, 3), 0.36], size=[x_top * 2 - 0.1, 0.04, 0.26], mass_kg=2.2, hp=160, attach="truss_L",
                         end=i in (0, 6)))
    for i, (s, sx) in enumerate([(s, sx) for s, sx in (("L", -1), ("R", 1)) for _ in range(2)]):
        k = i % 2
        y = 0.38 - k * 0.76
        mods.append(dict(id="cassette_%d%s" % (k, s), kind="solana_cassette", pos=[sx * 0.36, round(y, 3), 0.33], size=[0.66, 0.62, 0.17], mass_kg=46.0, hp=220,
                         attach="truss_%s" % s, kwh=6.0, cells="LFP pouch, in a slide-in aluminium cassette with a handle", swap="2 minutes at a Solana Swap"))
    for s, sx in (("L", -1), ("R", 1)):
        mods.append(dict(id="corner_F%s" % s, kind="solana_front_corner", pos=[sx * (track / 2 - 0.18), round(yf, 3), r], size=[0.36, 0.30, 0.36], mass_kg=8.0, hp=220,
                         attach="truss_%s" % s, suspension="double wishbones of tube, coil spring; disc brake"))
        mods.append(dict(id="corner_B%s" % s, kind="solana_rear_corner", pos=[sx * (track / 2 - 0.25), round(yb + 0.25, 3), r], size=[0.12, 0.62, 0.20], mass_kg=7.0, hp=220,
                         attach="truss_%s" % s, suspension="trailing arm, coil spring"))
    mods.append(dict(id="controller", kind="controller", pos=[0, round(yf - 0.4, 3), 0.42], size=[0.28, 0.20, 0.10], mass_kg=8.0, hp=100, attach="cross_1",
                     brains="two Thirty-Twos", heat="open fins"))
    mods += mounts("standard", L, zt)
    wl = wheels(axles, track, r, 12.0)
    for wmod in wl:
        if wmod["id"].startswith("wheel_B"):
            wmod.update(kind="wheel_hub_motor", mass_kg=36.0, motor="outer-rotor hub motor, ferrite magnets, 25 kW, 420 Nm", kw=25.0, nm=420.0)
    mods += wl
    return dict(id=id_, name="Solana Lattice L-%d" % round(wb * 10), deck_width_m=PATTERN["mount_x_m"]["standard"] * 2 + 0.1, mount_x_m=PATTERN["mount_x_m"]["standard"], maker="solana_cycle_and_motor", family="solana", board="solana_lattice", cls="standard",
                length_m=round(L, 3), width_m=W, track_m=track, wheel_r=r, wheelbase_m=wb, axles=axles, drive="rear (a motor in each rear hub)",
                steering="rack and pinion, mechanical", pack_kwh=24.0, power_kw=50.0, modules=mods)


def micro(id_, wb, track, r, deck, mount_x, name, hub=True):
    """A Solana micro board (2026-10-02): the Lattice made small for light vehicles -- carts, karts, mowers, scooters,
    chairs. Its own little Pattern: a lower deck (`deck_top_m`) and close mount rails; lugged truss sides, one slide-in
    cassette, rear hub motors (none on a bumper car's: a single motor under the seat drives it)."""
    L = wb + 2 * r + 0.12
    yf, yb = wb / 2, -wb / 2
    axles = [dict(tag="F", y=yf, steer=True, driven=False), dict(tag="B", y=yb, steer=False, driven=True)]
    mods = []
    for s_, sx in (("L", -1), ("R", 1)):
        mods.append(dict(id="truss_%s" % s_, kind="solana_truss", pos=[sx * mount_x, 0, deck - 0.10], size=[0.06, L - 0.1, 0.14], mass_kg=round(3.0 * L, 1),
                         hp=250, attach=None if s_ == "L" else "cross_0", tube="25 mm drawn chromoly in lugs", panels=4))
        mods.append(dict(id="mount_rail_%s" % s_, kind="mount_rail", pos=[sx * mount_x, 0, deck - 0.02], size=[0.04, L - 0.2, 0.03], mass_kg=1.5, hp=150,
                         attach="truss_%s" % s_, holes_every_m=0.25))
    for i in range(3):
        y = yf + 0.1 - i * (wb + 0.2) / 2
        mods.append(dict(id="cross_%d" % i, kind="solana_cross", pos=[0, round(y, 3), deck - 0.10], size=[mount_x * 2 - 0.04, 0.03, 0.12], mass_kg=0.8,
                         hp=100, attach="truss_L", end=i in (0, 2)))
    mods.append(dict(id="cassette", kind="solana_cassette", pos=[0, 0, deck - 0.12], size=[mount_x * 2 - 0.1, min(0.62, wb * 0.5), 0.10], mass_kg=round(14 * wb, 1),
                     hp=150, attach="truss_L", kwh=round(2.0 * wb, 1), cells="LFP pouch in a slide-in cassette", swap="a minute at a Solana Swap"))
    for s_, sx in (("L", -1), ("R", 1)):
        mods.append(dict(id="corner_F%s" % s_, kind="solana_front_corner", pos=[sx * (track / 2 - 0.10), yf, r], size=[0.16, 0.16, 0.18], mass_kg=3.0, hp=120,
                         attach="truss_%s" % s_, suspension="a swing axle on a coil"))
        mods.append(dict(id="corner_B%s" % s_, kind="solana_rear_corner", pos=[sx * (track / 2 - 0.12), yb + 0.12, r], size=[0.08, 0.30, 0.12], mass_kg=3.0,
                         hp=120, attach="truss_%s" % s_, suspension="a trailing arm"))
    mods.append(dict(id="controller", kind="controller", pos=[0, round(yf - 0.15, 3), deck - 0.06], size=[0.16, 0.12, 0.06], mass_kg=2.0, hp=60,
                     attach="cross_0", brains="a Thirty-Two", heat="open fins"))
    wl = wheels(axles, track, r, 4.0)
    if hub:
        for wmod in wl:
            if wmod["id"].startswith("wheel_B"):
                wmod.update(kind="wheel_hub_motor", mass_kg=10.0, motor="outer-rotor hub motor, ferrite magnets, 3 kW", kw=3.0, nm=120.0)
    mods += wl
    return dict(id=id_, name=name, deck_width_m=mount_x * 2 + 0.06, mount_x_m=mount_x, deck_top_m=deck, maker="solana_cycle_and_motor", family="solana",
                board="solana_micro", cls="micro", length_m=round(L, 3), width_m=track + 0.15, track_m=track, wheel_r=r, wheelbase_m=wb, axles=axles,
                drive="rear (a hub motor in each rear wheel)", steering="tiller or wheel, mechanical", pack_kwh=round(2.0 * wb, 1), power_kw=6.0, modules=mods)


def trailer(id_, deck_l, axle_ys, track, r, hitch, cls="standard", name=""):
    """A Harrow running gear (2026-10-02): an unpowered board for trailers -- two boxed rails and cross members, beam
    axles on leaf springs, the Pattern's mount rails, and a hitch: an A-frame tongue with a ball coupler, or a
    kingpin plate (and landing legs) for a semi trailer. The deck's middle is y = 0; the hitch is ahead of it."""
    zt = PATTERN["deck_top_m"]
    rail_x = PATTERN["mount_x_m"][cls] - 0.08
    yf, yb = deck_l / 2, -deck_l / 2
    axles = [dict(tag="B%d" % i, y=y, steer=False, driven=False) for i, y in enumerate(axle_ys)]
    mods = [dict(id="rail_%s" % s, kind="harrow_rail", pos=[sx * rail_x, 0, 0.40], size=[0.075, deck_l - 0.05, 0.15], mass_kg=round(12 * deck_l, 1), hp=900,
                 attach=None if s == "L" else "cross_0", tube="150 x 75 x 4 mm boxed steel") for s, sx in (("L", -1), ("R", 1))]
    n = max(3, int(deck_l / 0.9) + 1)
    for i in range(n):
        y = yf - 0.05 - i * (deck_l - 0.1) / (n - 1)
        mods.append(dict(id="cross_%d" % i, kind="harrow_cross", pos=[0, round(y, 3), 0.40], size=[rail_x * 2, 0.06, 0.10], mass_kg=6.0, hp=400, attach="rail_L"))
    mods += mounts(cls, deck_l, zt)
    for a in axles:
        mods.append(dict(id="axle_%s" % a["tag"], kind="harrow_dedion", pos=[0, a["y"], r], size=[track - 0.15, 0.10, 0.10], mass_kg=30.0, hp=500,
                         attach="rail_L", axle="a straight beam axle, unpowered, drum brakes worked by the coupling's overrun"))
        for s, sx in (("L", -1), ("R", 1)):
            mods.append(dict(id="leaf_%s%s" % (a["tag"], s), kind="harrow_leaf", pos=[sx * rail_x, a["y"], 0.30], size=[0.07, 1.0, 0.12], mass_kg=14.0, hp=400,
                             attach="rail_%s" % s))
            mods.append(dict(id="corner_%s%s" % (a["tag"], s), kind="harrow_hub", pos=[sx * (track / 2 - 0.12), a["y"], r], size=[0.16, 0.3, 0.3], mass_kg=8.0,
                             hp=300, attach="axle_%s" % a["tag"]))
    if hitch == "tongue":
        mods.append(dict(id="tongue", kind="harrow_tongue", pos=[0, round(yf + 0.55, 3), 0.45], size=[rail_x * 2, 1.1, 0.10], mass_kg=25.0, hp=600, attach="cross_0",
                         coupler="a 50 mm ball coupler and safety chains; a jockey wheel"))
    else:
        mods.append(dict(id="kingpin", kind="harrow_kingpin", pos=[0, round(yf - 0.9, 3), 0.48], size=[1.2, 1.4, 0.04], mass_kg=60.0, hp=900, attach="cross_1",
                         coupler="a 2-inch kingpin in an upper coupler plate"))
        mods.append(dict(id="landing_legs", kind="harrow_legs", pos=[0, round(yf - 2.6, 3), 0.25], size=[rail_x * 2 + 0.2, 0.2, 0.5], mass_kg=70.0, hp=500,
                         attach="cross_2"))
    mods += wheels(axles, track, r, 16.0)
    return dict(id=id_, name=name or "Harrow running gear %s" % id_[-3:].upper(), deck_width_m=PATTERN["mount_x_m"][cls] * 2 + 0.1,
                mount_x_m=PATTERN["mount_x_m"][cls], maker="harrow_motor_works", family="harrow", board="harrow_trailer", cls=cls,
                length_m=round(deck_l, 3), width_m=track + 0.25, track_m=track, wheel_r=r, wheelbase_m=round(abs(axle_ys[0] - axle_ys[-1]), 3),
                axles=axles, drive="none (towed)", steering="none", pack_kwh=0.0, power_kw=0.0, hitch=hitch, modules=mods)


BOARDS = [
    steward("steward_narrow", "narrow", 5, [1, 4], [0, 1]),
    steward("steward_broad", "broad", 7, [1, 6], [0]),
    steward("steward_heavy", "heavy", 10, [1, 6, 9], [0, 2]),
    steward("steward_tram", "heavy", 8, [1, 7], [0, 1]),        # a tram section's board: every wheel steers
    steward("steward_farm5", "farm", 5, [1, 4], [0]),          # tractors (2026-10-02)
    steward("steward_farm7", "farm", 7, [1, 6], [0]),          # row-crop tractors, backhoe loaders
    steward("steward_rail32", "rail", 32, [2, 5, 27, 30], []),  # passenger cars and locomotives (2026-10-02)
    steward("steward_rail22", "rail", 22, [2, 5, 17, 20], []),  # freight cars
    harrow("harrow_h27", 2.70),
    harrow("harrow_h31", 3.10),        # the long ladder: full-size SUVs and pickups (2026-10-02)
    carrow("carrow_k28", 2.80),
    carrow("carrow_k36", 3.60),        # the long keel: limousines and hearses (2026-10-02)
    solana("solana_l25", 2.50),
    # the Solana micro boards (2026-10-02)
    micro("solana_m20", 2.00, 1.30, 0.30, 0.42, 0.42, "Solana Micro M-20: UTVs and park mowers"),
    micro("solana_m16", 1.65, 1.05, 0.23, 0.36, 0.34, "Solana Micro M-16: golf and utility carts"),
    micro("solana_m12", 1.20, 0.92, 0.25, 0.40, 0.26, "Solana Micro M-12: ATVs and riding mowers"),
    micro("solana_m10", 1.05, 1.00, 0.14, 0.20, 0.30, "Solana Micro M-10: karts and bumper cars"),
    micro("solana_m06", 0.62, 0.56, 0.13, 0.22, 0.18, "Solana Micro M-06: scooters and power chairs"),
    # the trailers' running gear (2026-10-02)
    trailer("harrow_tr25", 2.5, [0.0], 1.70, 0.28, "tongue", name="Harrow running gear, single axle"),
    trailer("harrow_tr50", 5.0, [-0.35, 0.35], 1.90, 0.32, "tongue", cls="broad", name="Harrow running gear, tandem"),
    trailer("harrow_ts150", 15.0, [-5.4, -6.6], 2.10, 0.48, "kingpin", cls="heavy", name="Harrow semi-trailer gear, tandem"),
]


def main():
    for b in BOARDS:
        ids = [m["id"] for m in b["modules"]]
        assert len(ids) == len(set(ids)), b["id"]
        for m in b["modules"]:
            assert m["attach"] is None or m["attach"] in ids, (b["id"], m["id"], m["attach"])
        b["mass_kg"] = round(sum(m["mass_kg"] for m in b["modules"]), 1)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump({"_about": "The boards (vehicle platforms): tools/vehicles/platforms.py; canon in tools/bible/canon_industry.py; research/vehicles/skateboard_chassis.md",
                   "version": 1, "pattern": PATTERN, "boards": BOARDS}, f, indent=1)
    for b in BOARDS:
        print("%-16s %-44s %5.0f kg  %4.0f kWh  %4.0f kW  L %.2f  W %.2f  WB %.2f  %d modules" % (
            b["id"], b["name"], b["mass_kg"], b["pack_kwh"], b["power_kw"], b["length_m"], b["width_m"], b["wheelbase_m"], len(b["modules"])))


if __name__ == "__main__":
    main()
