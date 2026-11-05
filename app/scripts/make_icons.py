"""Draw the app icons from the PitchMe mark.

The mark is a dot with three arcs: a voice that reaches the room. It is the
same drawing as src/components/ui/logo.tsx, on its 44-unit grid.

Run from app/:  python3 scripts/make_icons.py   (needs Pillow)
"""

from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parent.parent / "assets" / "images"

PLUM = (74, 43, 68)
SAGE = (124, 152, 133)
CREAM = (248, 245, 240)
WHITE = (255, 255, 255)

# Each arc: start point x, half chord, radius, colour, opacity. All arcs are
# centred on the same row (y = 22) and bulge to the right.
DOT = (13.0, 22.0, 4.2)
ARCS = [
    (22.0, 6.5, 9.0, PLUM, 1.0),
    (28.5, 11.5, 17.0, SAGE, 1.0),
    (35.0, 16.5, 25.0, SAGE, 0.38),
]
STROKE = 2.2
SUPERSAMPLE = 4


def draw_mark(size: int, fill: float, mono: tuple[int, int, int] | None = None) -> Image.Image:
    """The mark on a transparent square. `fill` is the share of the side the
    44-unit grid takes up; `mono` draws every part in one colour."""
    big = size * SUPERSAMPLE
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    unit = big * fill / 44
    # The grid's content spans x 8.8..36.1; centre it on the canvas.
    offset_x = (big - unit * 44) / 2 + unit * (22 - (8.8 + 36.1) / 2)
    offset_y = (big - unit * 44) / 2

    def at(x: float, y: float) -> tuple[float, float]:
        return offset_x + x * unit, offset_y + y * unit

    for x, half, radius, colour, alpha in ARCS:
        arc = Image.new("RGBA", (big, big), (0, 0, 0, 0))
        centre_x = x - math.sqrt(radius**2 - half**2)
        angle = math.degrees(math.asin(half / radius))
        cx, cy = at(centre_x, 22)
        r = radius * unit
        # Pillow draws the stroke inward from the box edge; push the box out
        # by half a stroke so the line is centred on the radius, as in SVG.
        box = r + STROKE * unit / 2
        ImageDraw.Draw(arc).arc(
            (cx - box, cy - box, cx + box, cy + box),
            -angle,
            angle,
            fill=(*(mono or colour), 255),
            width=max(1, round(STROKE * unit)),
        )
        if alpha < 1:
            arc.putalpha(arc.getchannel("A").point(lambda a, k=alpha: round(a * k)))
        _round_ends(arc, cx, cy, r, angle, STROKE * unit, mono or colour, alpha)
        layer = Image.alpha_composite(layer, arc)

    dot_x, dot_y = at(DOT[0], DOT[1])
    dot_r = DOT[2] * unit
    ImageDraw.Draw(layer).ellipse(
        (dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r), fill=(*(mono or PLUM), 255)
    )
    return layer.resize((size, size), Image.Resampling.LANCZOS)


def _round_ends(img, cx, cy, r, angle, width, colour, alpha) -> None:
    """Round line caps, as the SVG draws them."""
    draw = ImageDraw.Draw(img)
    cap = width / 2
    for sign in (-1, 1):
        a = math.radians(angle * sign)
        x, y = cx + r * math.cos(a), cy + r * math.sin(a)
        draw.ellipse((x - cap, y - cap, x + cap, y + cap), fill=(*colour, round(255 * alpha)))


def on_background(mark: Image.Image, colour: tuple[int, int, int]) -> Image.Image:
    base = Image.new("RGBA", mark.size, (*colour, 255))
    return Image.alpha_composite(base, mark).convert("RGB")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # iOS wants no transparency in the app icon.
    on_background(draw_mark(1024, 0.62), CREAM).save(OUT / "icon.png")
    # Android crops the adaptive layers to a circle or squircle: keep the mark
    # inside the middle two thirds.
    draw_mark(1024, 0.46).save(OUT / "adaptive-icon.png")
    draw_mark(1024, 0.46, mono=WHITE).save(OUT / "monochrome-icon.png")
    draw_mark(400, 0.9).save(OUT / "splash-icon.png")
    on_background(draw_mark(48, 0.8), CREAM).save(OUT / "favicon.png")
    print(f"Icons written to {OUT}")


if __name__ == "__main__":
    main()
