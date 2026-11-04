"""A cave painting for the empty space under the session list.

Caveman painting style, after real rock art, on the terminal's own background: figures are
silhouettes in two pigments (dark brown and red ochre). `#` in a sprite is a solid filled cell,
other characters are thin painted lines. Props: a hide hut, a fire, fern trees, a hand stencil.

One ~30 s story (STORY ticks at FRAME_MS):

  walk in   mammoth and baby walk onto the wall, hunters leave their hut
  throw     the spear flies and sticks, the mammoth goes "!" and raises her trunk
  chase     the mammoth chases the hunters back into the hut and stops at the fire
  home      she turns and walks off with her baby
  anthem    the hunters come out, dance round the fire and scratch a wacky anthem into the rock
"""

FRAME_MS = 250  # 4 pictures a second
STORY = 120     # ticks: 30 s

# name: (fg xterm-256, bg xterm-256, fg basic, bg basic); bg None = the terminal's own background.
# Pigments light enough for dark terminals and dark enough for light ones.
_BROWN, _RED = 137, 131
PALETTE = {
    "wall": (None, None, None, None),
    "brown": (_BROWN, None, "yellow", None),
    "brown_fill": (_BROWN, _BROWN, "yellow", "yellow"),
    "red": (_RED, None, "red", None),
    "red_fill": (_RED, _RED, "red", "red"),
}

ANTHEMS = ["UGG UGG HOO!", "MAMMOTH BIG, UGG FAST!", "OOGA CHAKA OOGA!", "FIRE GOOD! HOO HOO!",
           "UGG RUN, UGG LIVE!"]

_FLIP = str.maketrans("()/\\<>[]{}", ")(\\/><][}{")


def _spr(lines, pigment="brown"):
    w = max(map(len, lines))
    return {"lines": [ln.ljust(w) for ln in lines], "pig": pigment, "w": w, "h": len(lines)}


def _mirror(sp):
    return dict(sp, lines=[ln[::-1].translate(_FLIP) for ln in sp["lines"]])


# --- big cast: silhouettes facing left -------------------------------------------------
_MAM_BODY = [
    r"     ######",
    r"   ##########",
    r"  ###############",
    r"  ####################",
    r" ########################",
    r"## # ####################",
]
MAMMOTH = [
    _spr(_MAM_BODY + [r"##  ) #####  ###  #####", r" ##_/ ####   ###   ####"]),
    _spr(_MAM_BODY + [r"##  ) ####  ####  ####", r" ##_/  ####  ###  ####"]),
]
TRUMPET = _spr([
    r"##   ######",
    r" ## ##########",
    r"  ###############",
    r"  ####################",
    r"   #######################",
    r"  ( #####################",
    r"   \_  ####  ###  #####",
    r"       ####  ###   ####",
])
BABY = [_spr([r"  ####", r" #######", r"## ######", r"#  ##  ##"]),
        _spr([r"  ####", r" #######", r"## ######", r"# ##   ##"])]
WALK = [_spr([r" o", r"/|\ ", r" |", r"/ \ "], "red"), _spr([r" o", r"/|\ ", r" |", r" |\ "], "red")]
THROW = _spr([r" o__", r"/|", r" |", r"/ \ "], "red")
PANIC = [_spr([r"\o/", r" |", r" |", r"/ \ "], "red"), _spr([r"\o/", r" |", r" |", r"| |"], "red")]
DANCE = [_spr([r"\o/", r" |", r" |", r"/ \ "], "red"), _spr([r"_o_", r" |", r" |", r"/ \ "], "red"),
         _spr([r"\o_", r" |", r" |", r"/ \ "], "red"), _spr([r"_o/", r" |", r" |", r"/ \ "], "red")]
HUT = _spr([r"    \  /", r"     \/", r"    /##\ ", r"   /####\ ", r"  /##/\##\ ", r" /##/  \##\ "])
FIRE = [_spr([r"  )", r" (#)", r" \=/"], "red"), _spr([r" (", r"  #)(", r" \=/"], "red"),
        _spr([r"   (", r" )#", r" \=/"], "red")]
FERN = _spr([r"\|/", r"\|/", r"\|/", r" |"])
HAND = _spr([
    r"      ##",
    r"   ## ## ##",
    r"   ## ## ##",
    r"## ## ## ##",
    r"## ## ## ##  ##",
    r"########### ##",
    r"#############",
    r" ##########",
    r"  ########",
], "red")

# --- small cast ------------------------------------------------------------------------
S_MAMMOTH = [_spr([r" .####.", r"(######`.", r" \ ## ##"]), _spr([r" .####.", r"(######`.", r" \## ## "])]
S_TRUMPET = _spr([r"# .####.", r" ######`.", r"   ## ##"])
S_BABY = [_spr([r".##.", r"## #"]), _spr([r".##.", r"#  #"])]
S_WALK = [_spr([r" o", r"/|\ ", r"/ \ "], "red"), _spr([r" o", r"/|\ ", r" |"], "red")]
S_PANIC = [_spr([r"\o/", r" |", r"/ \ "], "red"), _spr([r"\o/", r" |", r"| |"], "red")]
S_HUT = _spr([r"  /\ ", r" /##\ ", r"/#/\#\ "])
S_FIRE = [_spr([r"(", r"\=/"], "red"), _spr([r" )", r"\=/"], "red")]


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


def _layout(rows, cols):
    if rows < 4 or cols < 40:
        return None
    h = min(rows - 1, 14)
    big = h >= 9 and cols >= 90
    s = dict(h=h, w=cols, big=big, foot=h - 1)
    hut = HUT if big else S_HUT
    fire = FIRE if big else S_FIRE
    mam, baby = (MAMMOTH, BABY) if big else (S_MAMMOTH, S_BABY)
    s.update(hut_x=2, hut_w=hut["w"], door=2 + hut["w"] // 2 - 1)
    s["fire_x"] = 2 + hut["w"] + (6 if big else 4)
    s["fire_r"] = s["fire_x"] + fire[0]["w"]
    s["mw"], s["bw"] = mam[0]["w"], baby[0]["w"]
    s["graze"] = max(round(cols * 0.5), s["fire_r"] + (26 if big else 12))
    s["target"] = [s["graze"] - (12 if big else 6), s["graze"] - (20 if big else 11)]
    s["stop"] = s["fire_r"] + 2
    s["spots"] = [s["fire_r"] + 2, s["fire_x"] - 4 if big else s["fire_x"] - 3]
    return s


def cast(rows, cols, tick):
    """Where everyone is at this tick (the story, without drawing). None when no room.

    mammoth/baby: (x, facing, pose); hunters: list of (x, pose, facing) or None when inside
    the hut; spear: ("flying", x, lift) / ("stuck", x) / ("held", x) / None; anthem: text so far."""
    s = _layout(rows, cols)
    if not s:
        return None
    t = tick % STORY
    w, graze, stop, mw = s["w"], s["graze"], s["stop"], s["mw"]
    face, pose = "left", ("walk", (t // 2) % 2)
    if t < 24:
        mx = _lerp(t, 0, 24, w + 2, graze)
    elif t < 46:
        mx, pose = graze, ("walk", (t // 4) % 2)
    elif t < 56:
        mx, pose = graze, ("trumpet", 0)
    elif t < 78:
        mx, pose = _lerp(t, 56, 78, graze, stop), ("walk", t % 2)
    elif t < 86:
        mx, pose = stop, ("walk", 0)
    else:
        face, mx = "right", _lerp(t, 86, 104, stop, w + 4)
    bx = mx + mw + 2
    out = dict(s, t=t, mammoth=(mx, face, pose) if t < 104 else None,
               baby=(bx, face, ("walk", (t // 2) % 2)) if t < 104 else None)

    hunters, spear = [], None
    for i in range(2):
        tgt, h = s["target"][i], None
        if t < 16 or 72 <= t < 100:
            h = None                                       # inside the hut
        elif t < 40:
            h = (_lerp(t, 16 + i * 3, 40, s["door"], tgt), ("walk", (t // 2 + i) % 2), "right")
            if i == 0:
                spear = ("held", h[0] + 3)
        elif t < 48:
            h = (tgt, ("throw", 0) if i == 0 and t < 43 else ("walk", 0), "right")
        elif t < 56:
            h = (tgt, ("panic", t % 2), "left")
        elif t < 72:
            h = (_lerp(t, 56, 72 - i * 2, tgt, s["door"]), ("panic", (t + i) % 2), "left")
        else:
            x = _lerp(t, 100, 106, s["door"], s["spots"][i])
            h = (x, ("walk", (t + i) % 2) if t < 106 else ("dance", (t + i * 2) % 4), "right")
        hunters.append(h)
    sx0, sx1 = s["target"][0] + 4, graze - 3
    if 40 <= t < 46:
        spear = ("flying", _lerp(t, 40, 46, sx0, sx1), [0, 2, 3, 3, 2, 1][t - 40])
    elif 46 <= t < 86:
        spear = ("stuck", sx1)
    out.update(hunters=hunters, spear=spear)
    out["anthem"], out["anthem_at"] = "", None
    if t >= 104:  # sung over the dancers' heads, clear of the hut
        song = ANTHEMS[(tick // STORY) % len(ANTHEMS)]
        out["anthem"] = song[:min(len(song), (t - 104 + 1) * len(song) // 15)]
        xs = [hh[0] for hh in hunters if hh]
        mid = (min(xs) + max(xs) + 3) // 2
        ax = max(s["hut_x"] + s["hut_w"] + 1, mid - len(song) // 2)
        out["anthem_at"] = (s["foot"] - (WALK if s["big"] else S_WALK)[0]["h"], min(ax, w - len(song)))
    return out


class _Wall:
    def __init__(self, h, w):
        self.h, self.w = h, w
        self.ch = [[" "] * w for _ in range(h)]
        self.co = [["wall"] * w for _ in range(h)]

    def put(self, y, x, text, pig):
        for j, c in enumerate(text):
            if c != " " and 0 <= y < self.h and 0 <= x + j < self.w:
                self.ch[y][x + j] = c
                self.co[y][x + j] = pig + "_fill" if c == "#" else pig

    def sprite(self, sp, x, bottom):
        """Bottom aligned; each line is solid from its first to its last mark, so figures
        cover what is behind them instead of mixing with it."""
        top = bottom - sp["h"] + 1
        for i, ln in enumerate(sp["lines"]):
            core = ln.strip(" ")
            start = len(ln) - len(ln.lstrip(" "))
            y = top + i
            for j in range(start, start + len(core)):
                if 0 <= y < self.h and 0 <= x + j < self.w:
                    self.ch[y][x + j], self.co[y][x + j] = " ", "wall"
            self.put(y, x, ln, sp["pig"])


def scene(rows, cols, tick):
    """The painting as rows of (char, colour name); None when there is no room."""
    c = cast(rows, cols, tick)
    if not c:
        return None
    big, foot, w, h = c["big"], c["foot"], c["w"], c["h"]
    wall = _Wall(h, w)
    mam, trumpet, baby, walk, panic, dance, hut, fire = (
        (MAMMOTH, TRUMPET, BABY, WALK, PANIC, DANCE, HUT, FIRE) if big else
        (S_MAMMOTH, S_TRUMPET, S_BABY, S_WALK, S_PANIC, S_PANIC, S_HUT, S_FIRE))

    if big and h >= HAND["h"] + 2 and w >= 100:   # an old hand stencil, sprayed red
        hx, hy = w - HAND["w"] - 5, HAND["h"]
        for k in range(14):
            hv = _hash(k, 77)
            wall.put(hv % (HAND["h"] + 2), hx - 2 + (hv >> 5) % (HAND["w"] + 4), ".", "red")
        wall.sprite(HAND, hx, hy)
    if big:
        for fx in (round(w * 0.30), round(w * 0.66)):
            wall.sprite(FERN, fx, foot)

    wall.sprite(fire[c["t"] % len(fire)], c["fire_x"], foot)
    poses = {"walk": walk, "panic": panic, "dance": dance, "throw": [THROW] if big else walk}
    for hunter in c["hunters"]:
        if hunter:
            x, (name, k), facing = hunter
            sp = poses[name][k % len(poses[name])]
            wall.sprite(sp if facing == "right" else _mirror(sp), x, foot)
    wall.sprite(hut, c["hut_x"], foot)        # over the hunters: they vanish through the door

    for who, frames in (("baby", baby), ("mammoth", mam)):
        if c[who]:
            x, facing, (name, k) = c[who]
            sp = trumpet if name == "trumpet" else frames[k % len(frames)]
            wall.sprite(sp if facing == "left" else _mirror(sp), x, foot)
    mx = c["mammoth"][0] if c["mammoth"] else 0
    if 44 <= c["t"] < 52 or 78 <= c["t"] < 86:
        wall.put(foot - mam[0]["h"], mx + 4, "!", "brown")

    sp = c["spear"]
    if sp and sp[0] == "held":
        wall.put(foot - (2 if big else 1), sp[1], "---->" if big else "->", "brown")
    elif sp and sp[0] == "flying":
        wall.put(foot - 3 - sp[2], sp[1], "---->" if big else "->", "brown")
    elif sp:
        for y, x in ((foot - 1, sp[1]), (foot, sp[1] - 1)):
            if 0 <= x < w and wall.ch[y][x] == " ":
                wall.put(y, x, "/", "brown")

    if c["anthem"]:
        y, x = c["anthem_at"]
        wall.put(max(0, y), max(0, x), c["anthem"], "brown")
    return [list(zip(wall.ch[y], wall.co[y])) for y in range(h)]


def frame(rows, cols, tick):
    """The painting as plain text lines, or None."""
    cells = scene(rows, cols, tick)
    if cells is None:
        return None
    return ["".join(ch for ch, _ in row).rstrip() for row in cells]
