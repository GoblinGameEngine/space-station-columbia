#!/usr/bin/env python3
"""
gcmd.py -- command-line client for the Goblins game's DevBridge autoload
(godot_project/scripts/autoload/DevBridge.gd).

Built so driving/inspecting a RUNNING instance of the game doesn't need
xdotool + scrot + guessed pixel coordinates for everything -- that's slow,
imprecise, and stops working entirely if the desktop session locks. This
talks to a small TCP JSON command server the game itself runs (debug
builds only, 127.0.0.1 only) instead.

Every command needs a per-launch auth token (a fresh random string
DevBridge writes to a local file at startup, see DevBridge.gd's own
comment for why) -- this script finds and sends it automatically, no
setup needed for the normal workflow.

Typical session:
    cd ~/goblin-engine/godot_project
    nohup ~/newtons-garden/tools/godot4 --path . scenes/Main.tscn > /tmp/g.log 2>&1 &
    python3 ~/goblin-engine/tools/gcmd.py wait-ready          # instead of a guessed `sleep N`
    python3 ~/goblin-engine/tools/gcmd.py run "root.get_node('/root/MapEditorUI')._set_editing(true)"
    python3 ~/goblin-engine/tools/gcmd.py screenshot /tmp/out.png
    python3 ~/goblin-engine/tools/gcmd.py quit

Prefer `run`/`eval` calling a system's own methods directly over
`key`/`mouse_*` simulation wherever the target is OUR OWN UI code
(MapEditorUI, QuestEditorUI, etc.) -- it's exact and doesn't depend on
current on-screen layout. Reach for `key`/`mouse_*` for things that only
exist as real input (actual gameplay: WASD movement, mouse-look, firing)
or when you deliberately want to test the real input path end to end.
"""

import argparse
import json
import os
import socket
import sys
import time

DEFAULT_PORT = int(os.environ.get("GOBLINS_DEV_BRIDGE_PORT", "8765"))
HOST = "127.0.0.1"


def token_path() -> str:
    """Mirrors DevBridge.gd's _token_path_for() exactly -- both sides
    compute this independently rather than one telling the other, so
    there's no handshake needed before the very first authenticated
    command."""
    override = os.environ.get("GOBLINS_DEV_BRIDGE_TOKEN_FILE")
    if override:
        return override
    tmp_dir = os.environ.get("TMPDIR") or "/tmp"
    return f"{tmp_dir.rstrip('/')}/goblins_devbridge_{DEFAULT_PORT}.token"


def load_token() -> str:
    """Empty string (not an exception) if the file isn't there yet --
    lets `ping` keep working against a not-quite-ready or pre-auth
    instance; every other command will just get a clear auth error back
    from the server itself if the token is genuinely missing/wrong."""
    try:
        with open(token_path()) as f:
            return f.read().strip()
    except OSError:
        return ""

# Godot Key enum values worth having by name instead of memorizing
# integers (see scratchpad/dump_keys.gd in the session that built this,
# if these ever need re-deriving: they come straight from GDScript's
# global KEY_* constants, not guessed).
KEYCODES = {
    "TAB": 4194306, "ESCAPE": 4194305, "ENTER": 4194309, "SPACE": 32,
    "BACKSPACE": 4194308, "DELETE": 4194312,
    "UP": 4194320, "DOWN": 4194322, "LEFT": 4194319, "RIGHT": 4194321,
    "SHIFT": 4194325, "CTRL": 4194326, "ALT": 4194328,
}
for _i in range(1, 13):
    KEYCODES[f"F{_i}"] = 4194332 + (_i - 1)
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    KEYCODES[_c] = ord(_c)
for _d in "0123456789":
    KEYCODES[_d] = ord(_d)

MOUSE_BUTTONS = {"left": 1, "right": 2, "middle": 3, "wheel_up": 4, "wheel_down": 5}


def send(cmd: dict, timeout: float = 10.0) -> dict:
    if "token" not in cmd:
        token = load_token()
        if token:
            cmd = {**cmd, "token": token}
    with socket.create_connection((HOST, DEFAULT_PORT), timeout=timeout) as sock:
        sock.sendall((json.dumps(cmd) + "\n").encode("utf-8"))
        sock.settimeout(timeout)
        buf = b""
        while b"\n" not in buf:
            chunk = sock.recv(65536)
            if not chunk:
                break
            buf += chunk
    line = buf.split(b"\n", 1)[0]
    if not line:
        raise RuntimeError("empty response from DevBridge (is the game running with this build's DevBridge.gd?)")
    return json.loads(line.decode("utf-8"))


def resolve_key(name: str) -> int:
    name = name.strip()
    if name.upper() in KEYCODES:
        return KEYCODES[name.upper()]
    if name.isdigit():
        return int(name)
    raise SystemExit(f"unknown key name '{name}' -- known: {', '.join(sorted(KEYCODES))}, or pass a raw integer")


def print_result(resp: dict) -> None:
    print(json.dumps(resp, indent=2, ensure_ascii=False))


def cmd_wait_ready(args):
    deadline = time.time() + args.timeout
    last_err = None
    while time.time() < deadline:
        try:
            resp = send({"cmd": "ping"}, timeout=1.5)
            if resp.get("ok"):
                print_result(resp)
                return 0
        except (ConnectionRefusedError, socket.timeout, OSError) as e:
            last_err = e
        time.sleep(0.3)
    print(f"gave up after {args.timeout}s waiting for DevBridge on {HOST}:{DEFAULT_PORT} ({last_err})", file=sys.stderr)
    return 1


def cmd_raw(args):
    print_result(send(json.loads(args.json)))
    return 0


def cmd_simple(cmd_name, field_map):
    def handler(args):
        payload = {"cmd": cmd_name}
        for arg_name, field_name in field_map.items():
            val = getattr(args, arg_name, None)
            if val is not None:
                payload[field_name] = val
        print_result(send(payload))
        return 0
    return handler


def cmd_key_like(cmd_name):
    def handler(args):
        payload = {
            "cmd": cmd_name,
            "physical_keycode": resolve_key(args.key),
            "ctrl": args.ctrl, "shift": args.shift, "alt": args.alt,
        }
        if cmd_name == "key":
            payload["pressed"] = not args.release
        print_result(send(payload))
        return 0
    return handler


def cmd_mouse_button_like(cmd_name):
    def handler(args):
        payload = {"cmd": cmd_name, "button_index": MOUSE_BUTTONS.get(args.button, 1), "x": args.x, "y": args.y}
        if cmd_name == "mouse_button":
            payload["pressed"] = not args.release
        print_result(send(payload))
        return 0
    return handler


def cmd_run_like(cmd_name):
    def handler(args):
        code = args.code
        if args.file:
            with open(args.file) as f:
                code = f.read()
        print_result(send({"cmd": cmd_name, "code": code}, timeout=args.timeout))
        return 0
    return handler


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="command", required=True)

    sub.add_parser("ping").set_defaults(func=lambda a: (print_result(send({"cmd": "ping"})), 0)[1])
    sub.add_parser("help").set_defaults(func=lambda a: (print_result(send({"cmd": "help"})), 0)[1])
    sub.add_parser("quit").set_defaults(func=lambda a: (print_result(send({"cmd": "quit"})), 0)[1])

    wr = sub.add_parser("wait-ready", help="poll ping until the game responds (replaces a guessed `sleep N` after launch)")
    wr.add_argument("--timeout", type=float, default=30.0)
    wr.set_defaults(func=cmd_wait_ready)

    raw = sub.add_parser("raw", help="send a raw JSON command object")
    raw.add_argument("json")
    raw.set_defaults(func=cmd_raw)

    ev = sub.add_parser("eval", help="evaluate a single expression (Expression class)")
    ev.add_argument("code")
    ev.set_defaults(func=lambda a: (print_result(send({"cmd": "eval", "code": a.code})), 0)[1])

    for name, help_text in [("run", "run multi-statement GDScript (body of a function taking `root`)")]:
        r = sub.add_parser(name, help=help_text)
        r.add_argument("code", nargs="?", default="", help="GDScript source (omit if using --file)")
        r.add_argument("--file", help="read the code from this file instead")
        r.add_argument("--timeout", type=float, default=10.0, help="seconds to wait for the reply (long bakes)")
        r.set_defaults(func=cmd_run_like(name))

    sh = sub.add_parser("screenshot", help="save the current rendered frame to a PNG path")
    sh.add_argument("path")
    sh.set_defaults(func=cmd_simple("screenshot", {"path": "path"}))

    dt = sub.add_parser("dump_tree", help="dump a node's subtree (names/types/rects/text)")
    dt.add_argument("--path", default="/root")
    dt.add_argument("--depth", type=int, default=4)
    dt.set_defaults(func=lambda a: (print_result(send({"cmd": "dump_tree", "path": a.path, "max_depth": a.depth})), 0)[1])

    for name in ["key", "key_tap"]:
        k = sub.add_parser(name, help=f"{'tap (press+release)' if name == 'key_tap' else 'press or release'} a key by name (F2, TAB, X, CTRL+...) or raw keycode")
        k.add_argument("key")
        k.add_argument("--release", action="store_true", help="release instead of press (key only, ignored for key_tap)")
        k.add_argument("--ctrl", action="store_true")
        k.add_argument("--shift", action="store_true")
        k.add_argument("--alt", action="store_true")
        k.set_defaults(func=cmd_key_like(name))

    for name in ["press_action", "release_action"]:
        pa = sub.add_parser(name, help="press/release a named input action (project.godot [input])")
        pa.add_argument("action")
        pa.set_defaults(func=cmd_simple(name, {"action": "action"}))

    for name in ["mouse_button", "mouse_click"]:
        mb = sub.add_parser(name, help=f"{'tap (press+release)' if name == 'mouse_click' else 'press or release'} a mouse button at a screen position")
        mb.add_argument("--button", choices=list(MOUSE_BUTTONS), default="left")
        mb.add_argument("--release", action="store_true", help="release instead of press (mouse_button only)")
        mb.add_argument("x", type=float)
        mb.add_argument("y", type=float)
        mb.set_defaults(func=cmd_mouse_button_like(name))

    mm = sub.add_parser("mouse_motion", help="inject a mouse-motion event (dx/dy is the RELATIVE delta -- for camera-look drags)")
    mm.add_argument("--x", type=float, default=0)
    mm.add_argument("--y", type=float, default=0)
    mm.add_argument("--dx", type=float, default=0)
    mm.add_argument("--dy", type=float, default=0)
    mm.set_defaults(func=cmd_simple("mouse_motion", {"x": "x", "y": "y", "dx": "dx", "dy": "dy"}))

    wf = sub.add_parser("wait_frame", help="block until N more frames have rendered (replaces guessing a sleep duration)")
    wf.add_argument("--count", type=int, default=1)
    wf.set_defaults(func=cmd_simple("wait_frame", {"count": "count"}))

    rp = sub.add_parser("read_pixels", help="read RGBA of pixel(s) from the currently displayed frame, no PNG round-trip")
    rp.add_argument("points", help='JSON list of [x,y] pairs, e.g. \'[[10,20],[30,40]]\'')
    rp.set_defaults(func=lambda a: (print_result(send({"cmd": "read_pixels", "points": json.loads(a.points)})), 0)[1])

    rs = sub.add_parser("reload_shader", help="hot-reload a .gdshader file onto a node's material_override, no relaunch")
    rs.add_argument("node_path")
    rs.add_argument("shader_path")
    rs.set_defaults(func=lambda a: (print_result(send({"cmd": "reload_shader", "node_path": a.node_path, "shader_path": a.shader_path})), 0)[1])

    mw = sub.add_parser("mouse_wheel")
    mw.add_argument("--direction", choices=["up", "down"], default="up")
    mw.add_argument("--steps", type=int, default=1)
    mw.add_argument("--x", type=float, default=0)
    mw.add_argument("--y", type=float, default=0)
    mw.set_defaults(func=cmd_simple("mouse_wheel", {"direction": "direction", "steps": "steps", "x": "x", "y": "y"}))

    q = sub.add_parser("query", help="where things are, as text, without rendering (WorldQuery.gd): "
                       "near S X [R] [CATS] | find TEXT | ground S X | view [N] | check S X [R] | here")
    q.add_argument("op", choices=["near", "find", "ground", "view", "check", "here"])
    q.add_argument("args", nargs="*")

    def _query(a):
        r = send({"cmd": "query", "op": a.op, "args": a.args}, timeout=120)
        if r.get("ok"):
            print(r.get("result", ""))
            return 0
        print_result(r)
        return 1
    q.set_defaults(func=_query)

    args = p.parse_args()
    try:
        sys.exit(args.func(args) or 0)
    except (ConnectionRefusedError, socket.timeout, OSError) as e:
        print(f"could not reach DevBridge at {HOST}:{DEFAULT_PORT}: {e}\n"
              f"(is the game running? was it launched via the Godot editor binary, not an exported release build?)",
              file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
