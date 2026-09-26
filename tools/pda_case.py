#!/usr/bin/env python3
"""The NYNEX Communicator's case printing (godot_project/ui/pda/case_*.png): white on clear, tinted
silver by the game.
  case_nynex.png          the NYNEX wordmark (1984-97), from its artwork (tools/pda_case/nynex.svg)
  case_bell.png           the Bell System bell (Saul Bass, 1969; tools/pda_case/bell_1969.svg)
  case_communicator.png   "COMMUNICATOR" drawn in the NYNEX wordmark's manner: ultra-heavy letters,
                          stems 1/3 of the cap height, diagonal-cut corners in place of curves, tight
                          spacing, and neighbours fused on a shared stroke (the M M, as NYNEX's N Y N)
Needs rsvg-convert.
    python3 tools/pda_case.py
"""
import os
import re
import subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "pda_case")
OUT = os.path.join(HERE, "..", "godot_project", "ui", "pda")
TMP = os.path.join(SRC, "_tmp.svg")
HEIGHT_PX = 96                 # rendered height; the game scales it down smoothly

# COMMUNICATOR on NYNEX's grid: caps 36 high, stems 12, gaps 3.  Each letter: (width, [polygons]),
# a polygon a list of (x, y) from the top left; a second polygon of a letter is a counter (even-odd).
S, H, GAP = 12, 36, 3
LETTERS = {
    "C": (34, [[(9, 0), (34, 0), (34, 11), (15, 11), (12, 14), (12, 22), (15, 25), (34, 25), (34, 36), (9, 36),
                (0, 27), (0, 9)]]),
    "O": (36, [[(9, 0), (27, 0), (36, 9), (36, 27), (27, 36), (9, 36), (0, 27), (0, 9)],
               [(15, 12), (21, 12), (24, 15), (24, 21), (21, 24), (15, 24), (12, 21), (12, 15)]]),
    # the two M's as one shape, sharing their middle stem
    "MM": (80, [[(0, 36), (12, 36), (12, 17), (23, 31), (34, 17), (34, 36), (46, 36), (46, 17), (57, 31), (68, 17),
                 (68, 36), (80, 36), (80, 0), (69, 0), (57, 15), (45, 0), (35, 0), (23, 15), (11, 0), (0, 0)]]),
    "U": (36, [[(0, 0), (12, 0), (12, 24), (24, 24), (24, 0), (36, 0), (36, 27), (27, 36), (9, 36), (0, 27)]]),
    "N": (35, [[(0, 36), (12, 36), (12, 17), (23, 36), (35, 36), (35, 0), (23, 0), (23, 19), (12, 0), (0, 0)]]),
    "I": (12, [[(0, 0), (12, 0), (12, 36), (0, 36)]]),
    "A": (38, [[(0, 36), (12, 36), (14, 29), (24, 29), (26, 36), (38, 36), (26, 0), (12, 0)],
               [(16, 20), (22, 20), (19, 10)]]),
    "T": (36, [[(0, 0), (36, 0), (36, 11), (24, 11), (24, 36), (12, 36), (12, 11), (0, 11)]]),
    "R": (37, [[(0, 0), (27, 0), (36, 9), (36, 16), (30, 21), (37, 36), (24, 36), (19, 24), (12, 24), (12, 36),
                (0, 36)],
               [(12, 10), (22, 10), (24, 12), (24, 13), (22, 15), (12, 15)]]),
}
WORD = ["C", "O", "MM", "U", "N", "I", "C", "A", "T", "O", "R"]


def communicator_svg() -> str:
    x = 0
    paths = []
    for ch in WORD:
        w, polys = LETTERS[ch]
        d = ""
        for poly in polys:
            d += "M" + " L".join(f"{x + px},{py}" for px, py in poly) + " Z "
        paths.append(f'<path fill-rule="evenodd" fill="#fff" d="{d}"/>')
        x += w + GAP
    x -= GAP
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{x + 2}" height="{H + 2}" '
            f'viewBox="-1 -1 {x + 2} {H + 2}">' + "".join(paths) + "</svg>")


def whiten(svg: str, drop_registered=False) -> str:
    """The artwork's ink in white; its knock-outs (white) clear."""
    svg = re.sub(r'fill="#(?:FFFFFF|ffffff|fff)"', 'fill="none"', svg)
    svg = re.sub(r'fill="#[0-9A-Fa-f]{3,6}"', 'fill="#fff"', svg)
    svg = re.sub(r"fill:#[0-9A-Fa-f]{3,6}", "fill:#fff", svg)
    if drop_registered:
        # the (R) is the last four paths of the NYNEX artwork
        svg = re.sub(r"(<path[^>]*/>\s*){4}</g>", "</g>", svg)
    return svg


def render(svg: str, out: str) -> None:
    with open(TMP, "w") as f:
        f.write(svg)
    subprocess.run(["rsvg-convert", "-h", str(HEIGHT_PX), "-o", os.path.join(OUT, out), TMP], check=True)
    os.remove(TMP)


if __name__ == "__main__":
    render(whiten(open(os.path.join(SRC, "nynex.svg")).read(), drop_registered=True), "case_nynex.png")
    render(whiten(open(os.path.join(SRC, "bell_1969.svg")).read()), "case_bell.png")
    render(communicator_svg(), "case_communicator.png")
    print("case art ->", OUT)
