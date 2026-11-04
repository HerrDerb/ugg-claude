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
