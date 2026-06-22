from __future__ import annotations

import math
import random
from typing import Callable

from PIL import ImageDraw


def _draw_head(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, fill: tuple[int, int, int], outline: tuple[int, int, int]) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=fill, outline=outline, width=3)
    eye_y = cy - r // 5
    draw.ellipse((cx - r // 2, eye_y - 4, cx - r // 2 + 8, eye_y + 4), fill=outline)
    draw.ellipse((cx + r // 2 - 8, eye_y - 4, cx + r // 2, eye_y + 4), fill=outline)
    draw.arc((cx - 10, cy + 2, cx + 10, cy + 18), start=10, end=170, fill=outline, width=3)


def _limb(
    draw: ImageDraw.ImageDraw,
    start: tuple[int, int],
    end: tuple[int, int],
    color: tuple[int, int, int],
    width: int = 5,
) -> None:
    draw.line((*start, *end), fill=color, width=width)


def draw_stick_character(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    *,
    pose: str = "wave",
    scale: float = 1.0,
    skin: tuple[int, int, int] = (255, 224, 196),
    ink: tuple[int, int, int] = (55, 55, 55),
    accent: tuple[int, int, int] = (255, 107, 53),
) -> None:
    s = scale
    body_top = y + int(42 * s)
    hip = y + int(95 * s)
    foot_y = y + int(150 * s)
    shoulder_y = y + int(55 * s)

    _draw_head(draw, x, y + int(24 * s), int(24 * s), skin, ink)
    _limb(draw, (x, body_top), (x, hip), ink, int(6 * s))

    if pose == "wave":
        _limb(draw, (x, shoulder_y), (x - int(34 * s), y + int(18 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(30 * s), y + int(40 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(22 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(22 * s), foot_y), ink, int(5 * s))
    elif pose == "think":
        _limb(draw, (x, shoulder_y), (x - int(28 * s), y + int(34 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(18 * s), y + int(48 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(20 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(20 * s), foot_y), ink, int(5 * s))
        draw.ellipse((x + int(30 * s), y + int(6 * s), x + int(46 * s), y + int(22 * s)), outline=accent, width=3)
    elif pose == "mic":
        draw.rounded_rectangle(
            (x + int(24 * s), y + int(28 * s), x + int(36 * s), y + int(58 * s)),
            radius=4,
            fill=accent,
            outline=ink,
            width=2,
        )
        _limb(draw, (x, shoulder_y), (x - int(26 * s), y + int(42 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(32 * s), y + int(36 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(22 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(22 * s), foot_y), ink, int(5 * s))
    elif pose == "hug":
        draw.ellipse((x - int(42 * s), y + int(72 * s), x - int(18 * s), y + int(96 * s)), fill=(255, 180, 120), outline=ink, width=2)
        _limb(draw, (x, shoulder_y), (x - int(34 * s), y + int(72 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(34 * s), y + int(72 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(18 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(18 * s), foot_y), ink, int(5 * s))
    elif pose == "heart":
        hx, hy = x + int(36 * s), y + int(36 * s)
        draw.polygon(
            [(hx, hy + 10), (hx - 12, hy - 4), (hx, hy - 14), (hx + 12, hy - 4)],
            fill=accent,
        )
        _limb(draw, (x, shoulder_y), (x - int(24 * s), y + int(44 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(24 * s), y + int(44 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(20 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(20 * s), foot_y), ink, int(5 * s))
    elif pose == "sigh":
        draw.arc((x - int(46 * s), y - int(4 * s), x - int(18 * s), y + int(20 * s)), 200, 340, fill=accent, width=3)
        _limb(draw, (x, shoulder_y), (x - int(30 * s), y + int(58 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(24 * s), y + int(58 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(18 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(24 * s), foot_y), ink, int(5 * s))
    elif pose == "jump":
        _limb(draw, (x, shoulder_y), (x - int(36 * s), y + int(24 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(36 * s), y + int(24 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(30 * s), y + int(118 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(30 * s), y + int(118 * s)), ink, int(5 * s))
    elif pose == "point":
        _limb(draw, (x, shoulder_y), (x - int(24 * s), y + int(52 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(42 * s), y + int(30 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(20 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(20 * s), foot_y), ink, int(5 * s))
    elif pose == "cheer":
        _limb(draw, (x, shoulder_y), (x - int(38 * s), y + int(10 * s)), ink, int(5 * s))
        _limb(draw, (x, shoulder_y), (x + int(38 * s), y + int(10 * s)), ink, int(5 * s))
        _limb(draw, (x, hip), (x - int(26 * s), foot_y), ink, int(5 * s))
        _limb(draw, (x, hip), (x + int(26 * s), foot_y), ink, int(5 * s))
        for angle in (20, 90, 160):
            rad = math.radians(angle)
            sx = x + int(math.cos(rad) * 52 * s)
            sy = y + int(math.sin(rad) * 52 * s)
            draw.line((x, y + int(8 * s), sx, sy), fill=accent, width=3)
    else:
        draw_stick_character(draw, x, y, pose="wave", scale=scale, skin=skin, ink=ink, accent=accent)


def draw_doodles(draw: ImageDraw.ImageDraw, width: int, height: int, seed: int, accent: tuple[int, int, int]) -> None:
    rng = random.Random(seed)
    for _ in range(8):
        x = rng.randint(40, width - 40)
        y = rng.randint(40, height - 40)
        size = rng.randint(6, 14)
        shape = rng.choice(("star", "dot", "spark"))
        if shape == "dot":
            draw.ellipse((x, y, x + size, y + size), fill=accent)
        elif shape == "spark":
            draw.line((x, y, x + size, y + size), fill=accent, width=3)
            draw.line((x + size, y, x, y + size), fill=accent, width=3)
        else:
            draw.polygon(
                [
                    (x, y - size),
                    (x + size // 3, y),
                    (x, y + size),
                    (x - size // 3, y),
                ],
                fill=accent,
            )
