"""Cave paintings for the empty space under the session list."""

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


# --- moving hunt: mammoth runs left, hunter chases, spear flies, legs swap every tick ---

def _sprite(*frames):
    return [[line for line in f] for f in frames]


MAMMOTH = _sprite(
    [r"      __.--~~~~~~~~--.__",
     r"  .-''                  ''-.",
     r" / (o)                      \ ",
     r"(  _ )                       )",
     r" \| |\__.---.________.---.__/",
     r"  | |  ||   ||      ||   ||"],
    [r"      __.--~~~~~~~~--.__",
     r"  .-''                  ''-.",
     r" / (o)                      \ ",
     r"(  _ )                       )",
     r" \| |\__.---.________.---.__/",
     r"  | |  /\   /\      /\   /\ "],
)
HUNTER = _sprite(
    [r"\o/", r" |", r"/ \ "],
    [r" o/", r"/|", r" |\ "],
)
SMALL_MAMMOTH = _sprite(
    [r"(o)~~~~~~)", r" || ||  ||"],
    [r"(o)~~~~~~)", r" /\ /\  /\ "],
)
SMALL_HUNTER = _sprite([r" o/", r"/|"], [r"\o ", r" |\ "])

# (mammoth, hunter, gap between them, spear)
BIG_SCENE = (MAMMOTH, HUNTER, 14, "<---")
SMALL_SCENE = (SMALL_MAMMOTH, SMALL_HUNTER, 8, "<-")
_GROUND = "~~~^~~~~^^~~~~~~^~~~~~~^^^~~~"


def _width(sprite):
    return max(len(line) for f in sprite for line in f)


def period(cols, scene):
    """Ticks until the hunt starts over (mammoth enters right, hunter leaves left)."""
    mammoth, hunter, gap, _ = scene
    return cols + _width(mammoth) + gap + _width(hunter)


def _blit(canvas, sprite_frame, x, bottom):
    for i, line in enumerate(sprite_frame):
        row = canvas[bottom - len(sprite_frame) + 1 + i]
        for j, ch in enumerate(line):
            if ch != " " and 0 <= x + j < len(row):
                row[x + j] = ch


def frame(rows, cols, tick):
    """One picture of the hunt for the free space, or None when nothing fits."""
    for scene in (BIG_SCENE, SMALL_SCENE):
        mammoth, hunter, gap, spear = scene
        height = len(mammoth[0]) + 1
        if height < rows and _width(mammoth) + gap + _width(hunter) < cols:
            break
    else:
        return None
    t = tick % period(cols, scene)
    mx = cols - t                                   # mammoth runs left
    hx = mx + _width(mammoth) + gap                 # hunter follows
    canvas = [[" "] * cols for _ in range(height)]
    ground = height - 1
    _blit(canvas, mammoth[tick % 2], mx, ground - 1)
    _blit(canvas, hunter[(tick + 1) % 2], hx, ground - 1)
    sx = hx - 1 - len(spear) - (t % max(1, gap - len(spear)))  # spear flies from hunter
    _blit(canvas, [spear], sx, ground - 2)
    canvas[ground] = list((_GROUND * (cols // len(_GROUND) + 1))[:cols])
    return ["".join(r).rstrip() for r in canvas]
