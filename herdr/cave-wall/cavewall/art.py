"""A cave painting for the empty space under the session list.

Caveman painting style: bare rock lit by a flickering torch, few pigments (red ochre, charcoal,
chalk), stick hunters, a mammoth outline with ochre fur, handprints. One ~30 s story:

  walk in   mammoth and baby walk onto the wall, hunters creep in from the left
  throw     the spear arcs and sticks, the mammoth goes "!" and raises her trunk
  chase     the mammoth chases the hunters off the wall
  home      she turns and walks off with her baby
  anthem    the hunters sneak back, dance and scratch a wacky anthem into the rock
"""

FRAME_MS = 250  # 4 pictures a second
STORY = 120     # ticks: 30 s

# name: (xterm-256 colour, basic 8-colour fallback). "<name>_dim" = outside the torchlight.
PALETTE = {"rock": (238, "white"), "lit": (137, "yellow"), "redochre": (131, "red"),
           "charcoal": (244, "white"), "chalk": (223, "white")}

ANTHEMS = ["UGG UGG HOO!", "MAMMOTH BIG, UGG FAST!", "OOGA CHAKA OOGA!", "FIRE GOOD! HOO HOO!",
           "UGG RUN, UGG LIVE!"]

_FLIP = str.maketrans("()/\\<>[]{}", ")(\\/><][}{")


def _spr(lines, color, fur=""):
    """Sprite: lines in one pigment; characters in `fur` are painted red ochre."""
    w = max(map(len, lines))
    return {"lines": [ln.ljust(w) for ln in lines], "color": color, "fur": fur, "w": w, "h": len(lines)}


def _mirror(sp):
    return dict(sp, lines=[ln[::-1].translate(_FLIP) for ln in sp["lines"]])


MAMMOTH = [
    _spr([r"        .-~~~~~~~~~-.",
          r"     .-'  ,  ,  ,  ,  '-.",
          r"    / (o  ,  ,  ,  ,  ,  \ ",
          r"   ( (    ,  ,  ,  ,  ,   |",
          r"    \ \  .--.______.--.  /",
          r"     ) ) |  |      |  | |"], "charcoal", ","),
    _spr([r"        .-~~~~~~~~~-.",
          r"     .-'  ,  ,  ,  ,  '-.",
          r"    / (o  ,  ,  ,  ,  ,  \ ",
          r"   ( (    ,  ,  ,  ,  ,   |",
          r"    \ \  .--.______.--.  /",
          r"     ) ) /  /      \  \ \ "], "charcoal", ","),
]
TRUMPET = _spr([r"  \\    .-~~~~~~~~~-.",
                r"   \\.-'  ,  ,  ,  ,  '-.",
                r"    \ (o  ,  ,  ,  ,  ,  \ ",
                r"     \_   ,  ,  ,  ,  ,   |",
                r"       \_.--.______.--.  /",
                r"         |  |      |  | |"], "charcoal", ",")
BABY = [_spr([r"  .-~~~~-.", r" ( o , ,  )", r" ( (,|  |'"], "charcoal", ","),
        _spr([r"  .-~~~~-.", r" ( o , ,  )", r" ( (/  \ '"], "charcoal", ",")]
WALK = [_spr([r" o  /", r"/|\/", r"/ \ "], "redochre"), _spr([r" o  /", r"/|\/", r" |\ "], "redochre")]
CREEP = [_spr(["", r",_o /", r" /\/"], "redochre"), _spr(["", r",_o /", r"  |/\ "], "redochre")]
THROW = _spr([r" o__", r"/|", r"/ \ "], "redochre")
PANIC = [_spr([r"\o/", r" |", r"/ \ "], "redochre"), _spr([r"\o/", r" |", r" |\ "], "redochre")]
DANCE = [_spr([r"\o/", r" |", r"/ \ "], "redochre"), _spr([r"_o_", r" |", r"| |"], "redochre"),
         _spr([r" o/", r"/|", r"/ >"], "redochre"), _spr([r"\o", r" |\ ", r"< \ "], "redochre")]
HAND = _spr([r"  ||||", r" \    /", r"  '--'"], "redochre")
HAND_CHALK = _spr([r" ||||", r" \    /", r"  '--'"], "chalk")

S_MAMMOTH = [_spr([r"(o,,,,,,)", r" ) || ||"], "charcoal", ","),
             _spr([r"(o,,,,,,)", r" ) /\ /\ "], "charcoal", ",")]
S_TRUMPET = _spr([r"\(o,,,,,,)", r"   || ||"], "charcoal", ",")
S_BABY = [_spr([r"( ,,,)", r" | |"], "charcoal", ","), _spr([r"( ,,,)", r" /\ "], "charcoal", ",")]
S_WALK = [_spr([r"o/", r"/|"], "redochre"), _spr([r"o/", r"|\ "], "redochre")]
S_PANIC = [_spr([r"\o/", r"/ \ "], "redochre"), _spr([r"\o/", r" |\ "], "redochre")]
S_HAND = _spr([r"|||", r"'-'"], "redochre")


def _hash(*n):
    h = 2166136261
    for v in n:
        h = ((h ^ (v & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0x5BD1E995) & 0xFFFFFFFF
        h ^= h >> 15
    return h


def _lerp(t, t0, t1, a, b):
    if t <= t0:
        return a
    if t >= t1:
        return b
    return round(a + (b - a) * (t - t0) / (t1 - t0))


class _Wall:
    """Rock texture plus the torch: pigment outside the light is dimmed."""

    def __init__(self, h, w, t):
        self.h, self.w = h, w
        self.cx, self.cy = w * 0.42, h * 0.45
        self.r = max(h * 1.1, w * 0.28) + (_hash(t % STORY, 1) % 5) - 2   # flicker
        self.ch = [[" "] * w for _ in range(h)]
        self.co = [[None] * w for _ in range(h)]
        for y in range(h):
            for x in range(w):
                hv = _hash(x, y, 3)
                if hv % 13 == 0:
                    self.ch[y][x] = "..''`,:"[(hv >> 4) % 7]
                    self.co[y][x] = "lit" if self.lit(y, x) else "rock"

    def lit(self, y, x):
        return ((x - self.cx) / 2.2) ** 2 + (y - self.cy) ** 2 <= (self.r / 2.2) ** 2

    def put(self, y, x, text, color, opaque=False):
        for j, c in enumerate(text):
            if (c != " " or opaque) and 0 <= y < self.h and 0 <= x + j < self.w:
                self.ch[y][x + j] = c
                self.co[y][x + j] = None if c == " " else (color if self.lit(y, x + j) else color + "_dim")

    def sprite(self, sp, x, bottom):
        """Bottom aligned; solid between the first and last mark of each line (hides rock)."""
        top = bottom - sp["h"] + 1
        for i, ln in enumerate(sp["lines"]):
            core = ln.strip(" ")
            if not core:
                continue
            start = len(ln) - len(ln.lstrip(" "))
            for j in range(start, start + len(core)):
                c = ln[j]
                self.put(top + i, x + j, c, "redochre" if c in sp["fur"] else sp["color"], opaque=True)


def scene(rows, cols, tick):
    """The painting as rows of (char, colour name or None); None when there is no room."""
    if rows < 4 or cols < 40:
        return None
    t = tick % STORY
    h = min(rows - 1, 14)
    big = h >= 8 and cols >= 80
    w = cols
    wall = _Wall(h, w, tick)
    foot = h - 1

    mam, trumpet, baby, walk, panic, hand = (
        (MAMMOTH, TRUMPET, BABY, WALK, PANIC, HAND) if big else
        (S_MAMMOTH, S_TRUMPET, S_BABY, S_WALK, S_PANIC, S_HAND))
    creep = CREEP if big else S_WALK
    dance = DANCE if big else S_PANIC
    mw, bw = mam[0]["w"], baby[0]["w"]

    # old marks on the wall: handprints, ochre dots, a tally
    wall.sprite(hand, 2, hand["h"] - 1)
    if big:
        wall.sprite(HAND_CHALK, w - HAND_CHALK["w"] - 3, HAND_CHALK["h"])
        wall.put(1, w - 30, ".  .  .  .  .", "redochre")
        wall.put(0, w // 2 - 6, "||||  ||||  ||", "charcoal")

    graze = max(round(w * 0.5), 32 if big else 18)
    target = [graze - (12 if big else 6), graze - (19 if big else 10)]

    # --- mammoth and baby --------------------------------------------------------------
    left, m_sp = True, mam[(t // 2) % 2]
    if t < 24:
        mx = _lerp(t, 0, 24, w + 2, graze)
    elif t < 46:
        mx, m_sp = graze, mam[(t // 4) % 2]
    elif t < 56:
        mx, m_sp = graze, trumpet
    elif t < 78:
        mx, m_sp = _lerp(t, 56, 78, graze, 2), mam[t % 2]
    elif t < 86:
        mx, m_sp = 2, mam[0]
    else:
        left = False
        mx = _lerp(t, 86, 104, 2, w + 4)
    bx = mx + mw + 2 if left else mx + mw + 3
    if t >= 86:
        bx = mx + mw + 2
    b_sp = baby[(t // 2) % 2]
    if not left:
        m_sp, b_sp = _mirror(m_sp), _mirror(b_sp)
    if t < 104:
        wall.sprite(b_sp, bx, foot)
        wall.sprite(m_sp, mx, foot)
    if 44 <= t < 52:
        wall.put(foot - m_sp["h"], mx + 6, "!", "chalk")

    # --- hunters -----------------------------------------------------------------------
    dancers = []
    for i in range(2):
        if t < 16:
            continue
        if t < 40:
            x, sp = _lerp(t, 16 + i * 3, 40, -6 - i * 5, target[i]), creep[(t // 2 + i) % 2]
        elif t < 48:
            x = target[i]
            sp = THROW if big and i == 0 and t < 43 else walk[0]
        elif t < 56:
            x, sp = target[i], _mirror(panic[t % 2])
        elif t < 74:
            x, sp = _lerp(t, 56, 74 - i * 2, target[i], -6), _mirror(panic[(t + i) % 2])
        elif t < 100:
            continue
        else:
            spot = round(w * 0.42) + (i * 2 - 1) * (7 if big else 4)
            x = _lerp(t, 100, 106, -6 - i * 6, spot)
            sp = walk[(t + i) % 2] if t < 106 else dance[(t + i * 2) % len(dance)]
            dancers.append(x)
        wall.sprite(sp, x, foot)

    # --- spear: thrown at 40, sticks at 46, stays until the next story -----------------
    sx0, sx1 = target[0] + 4, graze - 3
    if 40 <= t < 46:
        x = _lerp(t, 40, 46, sx0, sx1)
        wall.put(foot - 2 - [0, 2, 3, 3, 2, 1][t - 40], x, "--->" if big else "->", "charcoal")
    elif t >= 46:
        wall.put(foot - 1, sx1, "/", "charcoal")
        wall.put(foot, sx1 - 1, "/", "charcoal")

    # --- the anthem, scratched letter by letter ----------------------------------------
    if t >= 104:
        song = ANTHEMS[(tick // STORY) % len(ANTHEMS)]
        n = min(len(song), (t - 104 + 1) * len(song) // 15)
        ax = max(0, round(w * 0.42) - len(song) // 2)
        wall.put(max(0, foot - (5 if big else 3)), ax, song[:n], "chalk", opaque=True)

    return [list(zip(wall.ch[y], wall.co[y])) for y in range(h)]


def frame(rows, cols, tick):
    """The painting as plain text lines, or None."""
    cells = scene(rows, cols, tick)
    if cells is None:
        return None
    return ["".join(c for c, _ in row).rstrip() for row in cells]
