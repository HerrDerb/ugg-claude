"""Cave paintings for the empty space under the session list."""
import math

BIG = [
    r"             __.--~~~~~~~~--.__",
    r"         .-''                  ''-.                \o       o/",
    r"        / (o)                      \                |\ <--- /|",
    r"       (  _ )                       )              / \     / \ ",
    r"        \| |\__.---.________.---.__/",
    r"         | |  ||   ||      ||   ||          \|/          (\_/)",
    r"   ~~~~~~^~^~~~^^~~~^^~~~~~~^^~~~^^~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
]

SMALL = [
    r"   (o)~~~~~~)    <--- o/   \|/",
    r"    || ||  ||          /|",
    r"  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
]


def pick(rows, cols):
    """Largest painting that fits in rows x cols with a margin, or None."""
    for painting in (BIG, SMALL):
        if len(painting) < rows and max(map(len, painting)) < cols:
            return painting
    return None




# =====================================================================================
# The hunt story: one long ~30 s scene in natural cave pigments.
#
#   dawn      sun climbs over the mountains, hunters snore in the cave, mammoth + baby walk in
#   graze     trunk swings, birds cross, two hunters sneak out
#   throw     spear arcs, sticks in the dirt, mammoth goes "!"
#   trumpet   PRRAAAH!, volcano coughs, birds flee
#   chase     the mammoth chases the hunters back into their cave (dust, panic, chants)
#   hmpf      mammoth snorts at the cave, turns, walks off with baby
#   dusk      sun sinks, pterodactyl glides by
#   night     moon, stars, fire dance and a wacky cave anthem
# =====================================================================================

STORY = 240  # ticks; the board draws 8 per second
DAY = 200    # sun is up for ticks [0, DAY), then night

# name: (xterm-256 colour, basic 8-colour fallback name)
PALETTE = {
    "ochre": (130, "yellow"), "umber": (136, "yellow"), "chalk": (230, "white"),
    "charcoal": (243, "white"), "redochre": (124, "red"), "earth": (94, "yellow"),
    "plant": (64, "green"), "water": (66, "cyan"), "sun": (178, "yellow"), "fire": (166, "red"),
    "lava": (160, "red"), "smoke": (246, "white"), "moon": (223, "white"), "star": (187, "white"),
}
_MASK = {"o": "ochre", "u": "umber", "c": "chalk", "k": "charcoal", "r": "redochre", "e": "earth",
         "p": "plant", "w": "water", "s": "sun", "f": "fire", "l": "lava", "m": "moon"}
_FLIP = str.maketrans("()/\\<>[]{}", ")(\\/><][}{")


def _spr(lines, mask=None, color=None):
    """A sprite: lines plus an optional colour mask (same shape, letters from _MASK)."""
    w = max(map(len, lines))
    lines = [ln.ljust(w) for ln in lines]
    mask = [m.ljust(w) for m in (mask or [""] * len(lines))]
    return {"lines": lines, "mask": mask, "color": color, "w": w, "h": len(lines)}


def _mirror(sp):
    return dict(sp, lines=[ln[::-1].translate(_FLIP) for ln in sp["lines"]],
                mask=[m[::-1] for m in sp["mask"]])


# --- big cast -------------------------------------------------------------------------
_MAM_TOP = [
    r"           __.---~~~~~~~---.__",
    r"       _.-' ,  ,  ,  ,  ,    '-._",
    r"     .'  ,  ,  ,  ,  ,  ,  ,     '.",
    r"    / (o)  ,  ,  ,  ,  ,  ,  ,     \ ",
]
_MAM_TOP_MASK = [
    "",
    "            k  k  k  k  k",
    "         k  k  k  k  k  k  k",
    "      kkk   k  k  k  k  k  k  k",
]
MAM_WALK = [
    _spr(_MAM_TOP + [
        r"   (   _.)                         |",
        r"  / / /  \.__.---.________.---.__  /",
        r" ( (  |    | |   | |      | |   | |",
        r"  \_\ '    '-'   '-'      '-'   '-'",
    ], _MAM_TOP_MASK + ["", "", " c", "  ccc"], "ochre"),
    _spr(_MAM_TOP + [
        r"   (   _.)                         |",
        r"  / / /  \.__.---.________.---.__  /",
        r" ( (  /   / /     \ \    / /     \ \ ",
        r"  \_\ '   '-'     '-'    '-'     '-'",
    ], _MAM_TOP_MASK + ["", "", " c", "  ccc"], "ochre"),
]
MAM_TRUMPET = _spr([
    r" \\        __.---~~~~~~~---.__",
    r"  \\   _.-' ,  ,  ,  ,  ,    '-._",
    r"   \\.'  ,  ,  ,  ,  ,  ,  ,     '.",
    r"    \ (O)  ,  ,  ,  ,  ,  ,  ,     \ ",
    r"     \__.)                         |",
    r"   ( (   \.__.---.________.---.__  /",
    r"    \_\   | |   | |      | |   | |",
    r"          '-'   '-'      '-'   '-'",
], _MAM_TOP_MASK[:1] + _MAM_TOP_MASK[1:] + ["", "   c", "    ccc"], "ochre")
BABY = [
    _spr([r"   _.~~~~~._", r" .' (o) , , '.", r"(  _)   , ,  )", r" \ \| |  | |'"],
         ["", "    kkk", "", ""], "umber"),
    _spr([r"   _.~~~~~._", r" .' (o) , , '.", r"(  _)   , ,  )", r"  \ / /  \ \ "],
         ["", "    kkk", "", ""], "umber"),
]
H_WALK = [_spr([r" o  /", r"/|\/", r"/ \ "], color="redochre"),
          _spr([r" o  /", r"/|\/", r" |\ "], color="redochre")]
H_SNEAK = [_spr(["", r" ,_o/", r" /\ "], color="redochre"),
           _spr(["", r" ,_o/", r"  |\ "], color="redochre")]
H_THROW = _spr([r" o__", r"/|", r"/ \ "], color="redochre")
H_PANIC = [_spr([r"\o/", r" |", r"/ \ "], color="redochre"),
           _spr([r"\o/", r" |", r" |\ "], color="redochre")]
H_DANCE = [_spr([r"\o/", r" |", r"/ \ "], color="redochre"),
           _spr([r"_o_", r" |", r"| |"], color="redochre"),
           _spr([r" o/", r"/|", r"/ >"], color="redochre"),
           _spr([r"\o ", r" |\ ", r"< \ "], color="redochre")]
H_SLEEP = _spr(["", "", r"o=="], color="redochre")
H_CLUB = [_spr([r" o @", r"/|/", r"/ \ "], ["   e"], "redochre"),
          _spr([r" o @", r"/|/", r" |\ "], ["   e"], "redochre")]
CAVE = _spr([
    r"      __..------..__",
    r"   .-'##   ~~~~   ##'-.",
    r"  /##/              \##\ ",
    r" /##/                \##\ ",
    r"|###|                |###|",
    r"|###|                |###|",
    r"|###|                |###|",
], ["", "     kk            kk", "   kk              kk", "  kk                kk",
    " kkk                kkk", " kkk                kkk", " kkk                kkk"], "earth")
FIRE = [_spr([r"  )", r" ( )", r"_\_/_"], ["  f", " fff", "eeeee"]),
        _spr([r" (", r"  ) (", r"_\_/_"], [" f", "  f f", "eeeee"]),
        _spr([r"   (", r" )(", r"_\_/_"], ["   f", " ff", "eeeee"])]
PINE = _spr([r"   /\ ", r"  /  \ ", r" /    \ ", r"/______\ ", r"   ||"],
            ["   pp", "  p  p", " p    p", "pppppppp", "   ee"])
OAK = _spr([r"  .-~~-.", r" ( ,,,, )", r"( ,,,,,, )", r" '-.__.-'", r"    ||"],
           ["  pppppp", " pppppppp", "pppppppppp", " pppppppp", "    ee"])
SUN = _spr([r"\ | /", r"- O -", r"/ | \ "], color="sun")
MOON = _spr([r" .-.", r"(  (", r" '-'"], color="moon")
CLOUD = _spr([r"  .--.", r".(    ).", r" '----'"], color="chalk")
PTERO = [_spr([r"__\v/__"], color="charcoal"), _spr([r"  /v\ "], color="charcoal")]

# --- small cast (for little free space) ------------------------------------------------
S_MAM = [_spr([r"(o)~~~~~~)", r" || ||  ||"], ["kkk"], "ochre"),
         _spr([r"(o)~~~~~~)", r" /\ /\  /\ "], ["kkk"], "ochre")]
S_MAM_TRUMPET = _spr([r"\(O)~~~~~~)", r"  || ||  ||"], [" kkk"], "ochre")
S_BABY = [_spr([r"(o)~~)", r" || |"], ["kkk"], "umber"), _spr([r"(o)~~)", r" /\ \ "], ["kkk"], "umber")]
S_H = [_spr([r"o/", r"/|"], color="redochre"), _spr([r"o/", r"|\ "], color="redochre")]
S_PANIC = [_spr([r"\o/", r"/ \ "], color="redochre"), _spr([r"\o/", r" |\ "], color="redochre")]
S_CAVE = _spr([r" .--. ", r"|#  #|"], color="earth")
S_FIRE = [_spr([r"^"], color="fire"), _spr([r"*"], color="fire")]

ANTHEMS = ["UGG UGG HOO!", "MAMMOTH BIG, UGG FAST!", "OOGA CHAKA OOGA!", "FIRE GOOD! HOO HOO!"]


class _Canvas:
    def __init__(self, h, w):
        self.h, self.w = h, w
        self.ch = [[" "] * w for _ in range(h)]
        self.co = [[None] * w for _ in range(h)]

    def put(self, y, x, text, color=None, opaque=False):
        if not 0 <= y < self.h:
            return
        for j, c in enumerate(text):
            if (c != " " or opaque) and 0 <= x + j < self.w:
                self.ch[y][x + j], self.co[y][x + j] = c, color

    def sprite(self, sp, x, bottom):
        """Bottom-aligned; inside each line (first to last mark) the sprite is solid."""
        top = bottom - sp["h"] + 1
        for i, (ln, mk) in enumerate(zip(sp["lines"], sp["mask"])):
            core = ln.strip(" ")
            if not core:
                continue
            start = len(ln) - len(ln.lstrip(" "))
            for j in range(start, start + len(core)):
                y, xx = top + i, x + j
                if 0 <= y < self.h and 0 <= xx < self.w:
                    self.ch[y][xx] = ln[j]
                    self.co[y][xx] = _MASK.get(mk[j], sp["color"]) if mk[j] != " " else sp["color"]


def _lerp(t, t0, t1, a, b):
    if t <= t0:
        return a
    if t >= t1:
        return b
    return round(a + (b - a) * (t - t0) / (t1 - t0))


def _hash(*n):
    h = 2166136261
    for v in n:
        h = ((h ^ (v & 0xFFFFFFFF)) * 16777619) & 0xFFFFFFFF
        h ^= h >> 13
        h = (h * 0x5BD1E995) & 0xFFFFFFFF
        h ^= h >> 15
    return h


def period(cols=None):
    """Ticks until the story starts over (the same for every width)."""
    return STORY


def _sky(cv, t, sky_rows, horizon):
    w = cv.w
    night = t >= DAY or t < 12
    if night or t < 24:  # stars, fading at dawn
        for y in range(sky_rows):
            for x in range(0, w, 1):
                hv = _hash(x, y, 7)
                if hv % 23 == 0 and (night or hv % 3 == 0):
                    cv.put(y, x, "*" if (hv + t // 3) % 5 == 0 else ".", "star")
    if t < DAY and sky_rows >= 2:
        f = t / DAY
        x = round(1 + f * (w - SUN["w"] - 2))
        low = horizon  # starts and ends behind the mountains
        y_bottom = round(low - (low - (SUN["h"] - 1)) * math.sin(math.pi * f))
        cv.sprite(SUN, x, y_bottom)
    elif sky_rows >= 2:
        f = (t - DAY) / (STORY - DAY)
        cv.sprite(MOON, round(w * 0.15 + f * w * 0.5), MOON["h"] - 1 + (1 if sky_rows > 4 else 0))
    for i, x0 in enumerate((5, w // 2 + 7)):  # clouds drift, one lap per story
        if sky_rows >= 4:
            x = (x0 + t * (w + 12) // STORY) % (w + 12) - 10
            cv.sprite(CLOUD, x, CLOUD["h"] - 1 + i)
    if 20 <= t < 90 and sky_rows >= 2:  # morning flock, flapping
        for k, (dx, dy) in enumerate(((0, 1), (3, 0), (6, 1), (9, 0))):
            cv.put(dy, _lerp(t, 20, 90, -10, w + 2) + dx, "v" if (t // 2 + k) % 2 else "~", "charcoal")
    if 176 <= t < 216 and sky_rows >= 2:  # dusk glider
        cv.sprite(PTERO[(t // 3) % 2], _lerp(t, 176, 216, w + 2, -10), 1)


def _mountains(cv, t, top, base):
    """One connected ridgeline with snowy peaks and a smoking volcano. Whatever is behind the
    ridge (setting sun, stars, clouds) is hidden, so the sun really sinks behind the mountains."""
    w, height = cv.w, base - top + 1
    vx, vh = round(w * 0.72), height
    peaks, x = [], 3
    while x < w + 8:
        if abs(x - vx) > vh + 3:
            peaks.append((x, 2 + _hash(x, 3) % max(1, height - 2)))
        x += 9 + _hash(x, 5) % 10

    def elev(x):
        e = max([1] + [ph - abs(x - px) for px, ph in peaks])  # 1: low hills between peaks
        return max(e, min(vh, vh + 1 - abs(x - vx)))  # volcano: flat crater on top

    ev = [elev(x) for x in range(-1, w + 1)]       # ev[x + 1] is column x
    for x in range(w):
        for y in range(base - ev[x + 1] + 1, base + 1):
            cv.put(y, x, " ", opaque=True)         # rock face hides what is behind
            if _hash(x, y, 9) % 17 == 0:
                cv.put(y, x, ".", "charcoal")
    peak_tops = {px: ph for px, ph in peaks}
    for x in range(w):
        e0, e1 = ev[x + 1], ev[x + 2]
        if e1 > e0:
            y, ch = base - e0, "/"
        elif e1 < e0:
            y, ch = base - e1, "\\"
        elif e0 > 0:
            y, ch = base - e0, "_"
        else:
            continue
        snowy = any(abs(x - px) <= 1 and ph >= 4 and base - y >= ph - 1 for px, ph in peak_tops.items())
        if e0 == vh and e1 == vh:  # crater: lava sits between the rims
            cv.put(y + 1, x, "~^~"[(x + t // 2) % 3] if t % 8 < 6 else "~", "lava")
            continue
        cv.put(y, x, ch, "chalk" if snowy else "charcoal")
    angry = 112 <= t < 140
    for i in range(6 if angry else 4):  # puffs rise and drift east
        age = (t + i * 9) % 36
        y = top - 1 - age // 6
        if y < 0:
            continue
        puff = ("o", "O", "()", "( )", "(  )", "(   )")[min(5, age // 6)]
        cv.put(y, vx + age // 5, puff, "smoke")
    if angry:
        for i in range(5):
            hv = _hash(t, i)
            cv.put(top - 1 - hv % 3, vx - 3 + hv % 7, "*'."[hv % 3], "lava")


def _ground(cv, t, y, river):
    w = cv.w
    for x in range(w):
        hv = _hash(x, 11)
        cv.put(y, x, "_.,_'_._"[hv % 8], "earth")
    r0, r1 = river
    for x in range(r0, r1):
        cv.put(y, x, "~-~~^~"[(x + t // 2) % 6], "water")


def scene(rows, cols, tick):
    """The painting as rows of (char, colour name); None when there is no room."""
    if rows < 4 or cols < 40:
        return None
    t = tick % STORY
    h = min(rows - 1, 22)
    big = h >= 10 and cols >= 100
    cv = _Canvas(h, cols)
    ground = h - 1
    stand = ground - 1                      # feet row
    w = cols
    river = (round(w * 0.80), round(w * 0.80) + max(4, w // 12))

    cave, mam, baby, walk, panic, fire = ((CAVE, MAM_WALK, BABY, H_WALK, H_PANIC, FIRE) if big else
                                          (S_CAVE, S_MAM, S_BABY, S_H, S_PANIC, S_FIRE))
    mw, bw = mam[0]["w"], baby[0]["w"]
    trumpet = MAM_TRUMPET if big else S_MAM_TRUMPET
    cave_x, cave_r = 1, 1 + cave["w"]
    inside = [cave_x + (6 if big else 1), cave_x + (16 if big else 3)]
    graze = max(cave_r + 34 if big else cave_r + 14, min(round(w * 0.5), river[0] - mw - bw - 4))

    # --- background: sky, mountains, trees -------------------------------------------
    fg_top = stand - mam[0]["h"] + 1
    if big and h >= 15:
        m_base = fg_top                     # horizon: behind and above the foreground cast
        m_top = max(3, m_base - 5)
        _sky(cv, t, m_top, m_base)
        _mountains(cv, t, m_top, m_base)
    else:
        _sky(cv, t, max(0, fg_top - 1), max(0, fg_top - 1))
    if big:
        for tree, fx in ((PINE, 0.38), (OAK, 0.66), (PINE, 0.93), (OAK, 0.30)):
            tx = round(w * fx)
            if tx + tree["w"] < w and not (river[0] - tree["w"] <= tx <= river[1]):
                cv.sprite(tree, tx, stand)
        for gx in range(cave_r + 3, w - 3, 9):  # grass tufts
            if not river[0] - 2 <= gx <= river[1]:
                cv.put(stand, gx + _hash(gx) % 4, ("\\|/", ",|,", "\\,/")[_hash(gx, 2) % 3], "plant")
    _ground(cv, t, ground, river)

    # --- cave and fire ----------------------------------------------------------------
    cv.sprite(cave, cave_x, stand)
    fx = cave_x + (cave["w"] - fire[0]["w"]) // 2 + (0 if big else 1)
    cv.sprite(fire[t % len(fire)], fx, stand)

    # --- cast positions for this tick --------------------------------------------------
    m_face_left, m_sp, m_x = True, mam[(t // 3) % 2], 0
    if t < 48:
        m_x = _lerp(t, 0, 48, w + 2, graze)
    elif t < 112:
        m_x = graze
        m_sp = mam[(t // 6) % 2]          # grazing: slow trunk / leg shuffle
    elif t < 120:
        m_x, m_sp = graze, trumpet
    elif t < 160:
        m_x = _lerp(t, 120, 160, graze, cave_r + 1)
        m_sp = mam[t % 2]                 # charging: legs at full speed
    elif t < 172:
        m_x = cave_r + 1
        m_sp = mam[0]
    else:
        m_face_left = False
        m_x = _lerp(t, 172, 216, cave_r + 1, w + 4)
        m_sp = mam[(t // 3) % 2]
    b_x = m_x + mw + 2 if m_face_left else m_x - bw - 2
    if 48 <= t < 112:
        b_x += (t // 8) % 3 - 1           # baby fidgets
    if t >= 172:
        b_x = m_x + mw + 3                # baby leads the way home
    b_sp = baby[(t // 3) % 2]
    if not m_face_left:
        m_sp, b_sp = _mirror(m_sp), _mirror(b_sp)
    cv.sprite(b_sp, b_x, stand)
    cv.sprite(m_sp, m_x, stand)

    hunters = []                          # (sprite, x)
    target = [graze - (16 if big else 8), graze - (24 if big else 12)]
    for i in range(2):
        club = big and i == 1
        home = inside[1 - i]  # the front hunter sleeps by the door
        if t < 48:
            sp = H_SLEEP if big else S_H[0]
            x = home
            if big and (t // 6 + i) % 2:
                cv.put(stand - 2 - (t // 4 + i) % 3, x + 2 + i, "zZ"[(t // 5 + i) % 2], "chalk")
        elif t < 96:
            x = _lerp(t, 48 + i * 6, 96, home, target[i])
            sneak = H_SNEAK if big else S_H
            sp = (H_CLUB if club else sneak)[(t // 3) % 2]
        elif t < 120:
            x = target[i]
            sp = H_THROW if big and i == 0 and t < 104 else (H_CLUB[0] if club else walk[0])
            if t >= 106:
                sp = _mirror(panic[t % 2])
        elif t < 150:
            x = _lerp(t, 120, 150 - i * 4, target[i], home)
            sp = _mirror(panic[t % 2])
        elif t < 216:
            x, sp = home, walk[0]
        else:
            x, sp = home + (t // 4 + i) % 2, (H_DANCE if big else S_PANIC)[(t // 3 + i * 2) % (4 if big else 2)]
        hunters.append((sp, x))
        cv.sprite(sp, x, stand)

    # spear: thrown at 100, sticks in the dirt at 108, stays till the next story
    sx0, sx1 = target[0] + 4, graze - 4
    if 100 <= t < 108:
        x = _lerp(t, 100, 108, sx0, sx1)
        arc = [0, 2, 3, 3, 3, 2, 1, 0][t - 100]
        cv.put(stand - 2 - arc, x, "--->" if big else "->", "earth")
    elif t >= 108:
        cv.put(stand - 1, sx1, "/", "earth")
        cv.put(stand, sx1 - 1, "/", "earth")

    # dust behind the charging mammoth
    if 120 <= t < 160:
        for k in range(4):
            cv.put(stand - (k % 2), m_x + mw + 1 + k * 2 + (t % 2), ".o,"[(t + k) % 3], "earth")

    # --- speech, carved in chalk -------------------------------------------------------
    def say(text, x, y):
        cv.put(max(0, y), max(0, min(x, w - len(text) - 1)), f" {text} ", "chalk", opaque=True)
    mtop = stand - m_sp["h"]
    if 106 <= t < 112:
        say("!", m_x + 6, mtop)
    if 112 <= t < 124:
        say("PRRAAAH!", m_x - 2, mtop)
    if 108 <= t < 150:
        for sp, x in hunters:
            say("!", x + 1, stand - sp["h"])
        if 124 <= t < 150:
            say("RUN RUN RUN!", hunters[0][1] - 2, stand - 4)
    if 160 <= t < 172:
        say("hmpf.", m_x + 4, mtop)
    if t >= 218:
        say(ANTHEMS[(t - 218) // 6 % len(ANTHEMS)], cave_x + 2, stand - (cave["h"] if big else 2) - 1)

    return [list(zip(cv.ch[y], cv.co[y])) for y in range(h)]


def frame(rows, cols, tick):
    """The painting as plain text lines, or None."""
    cells = scene(rows, cols, tick)
    if cells is None:
        return None
    return ["".join(c for c, _ in row).rstrip() for row in cells]
