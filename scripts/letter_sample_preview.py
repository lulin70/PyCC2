"""Render a comparison sheet: current badge vs centered letter vs both.

Uses the same drawing logic as the in-game unit identity overlay so the
sample matches production rendering closely.
"""

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

import pygame

pygame.init()

W, H = 1100, 640
surface = pygame.Surface((W, H))
surface.fill((44, 48, 56))
font = pygame.font.Font(None, 26)

TILE = 48  # production sprite size at zoom 1.0

ALLIED = (45, 70, 110)
AXIS = (105, 45, 45)


def draw_base(surf, cx, cy, faction, zoom):
    w = int(34 * zoom)
    h = int(13 * zoom)
    color = ALLIED if faction == "allies" else AXIS
    ellipse = pygame.Rect(0, 0, w, h)
    ellipse.center = (cx, cy + int(16 * zoom))
    base = pygame.Surface((w, h), pygame.SRCALPHA)
    pygame.draw.ellipse(base, (*color, 120), base.get_rect())
    surf.blit(base, ellipse)


def draw_sprite_body(surf, cx, cy, kind, zoom):
    """Rough unit silhouette so the sample looks like the game."""
    color = (200, 200, 200)
    if kind == "infantry":
        pygame.draw.circle(surf, color, (cx, cy), int(10 * zoom))
        pygame.draw.circle(surf, color, (cx - int(7 * zoom), cy + int(8 * zoom)), int(5 * zoom))
        pygame.draw.circle(surf, color, (cx + int(7 * zoom), cy + int(8 * zoom)), int(5 * zoom))
    elif kind == "tank":
        r = pygame.Rect(0, 0, int(30 * zoom), int(18 * zoom))
        r.center = (cx, cy)
        pygame.draw.rect(surf, color, r, border_radius=4)
        pygame.draw.rect(
            surf,
            (140, 140, 140),
            (cx - int(16 * zoom), cy + int(6 * zoom), int(32 * zoom), int(6 * zoom)),
        )
    elif kind == "mg":
        pygame.draw.circle(surf, color, (cx, cy), int(9 * zoom))
        pygame.draw.line(
            surf, color, (cx - int(10 * zoom), cy), (cx + int(10 * zoom), cy), int(3 * zoom)
        )
    elif kind == "gun":
        pygame.draw.circle(surf, color, (cx, cy), int(9 * zoom))
        pygame.draw.line(
            surf, color, (cx, cy), (cx + int(14 * zoom), cy - int(10 * zoom)), int(3 * zoom)
        )


def draw_badge(surf, cx, cy, shape, zoom):
    s = max(8, int(10 * zoom))
    r = s // 2 + 2
    pygame.draw.circle(surf, (25, 25, 25), (cx, cy - int(16 * zoom)), r)
    bx, by = cx, cy - int(16 * zoom)
    if shape == "square":
        pygame.draw.rect(surf, (255, 255, 255), (bx - r + 3, by - r + 3, 2 * r - 6, 2 * r - 6))
    elif shape == "triangle":
        pygame.draw.polygon(
            surf,
            (255, 255, 255),
            [(bx, by - r + 3), (bx + r - 3, by + r - 3), (bx - r + 3, by + r - 3)],
        )
    elif shape == "double_dot":
        d = max(2, r // 2)
        pygame.draw.circle(surf, (255, 255, 255), (bx - d, by), d)
        pygame.draw.circle(surf, (255, 255, 255), (bx + d, by), d)
    else:
        pygame.draw.circle(surf, (255, 255, 255), (bx, by), max(2, r - 4))


def draw_letter(surf, cx, cy, letter, zoom):
    radius = max(7, int(11 * zoom))
    pygame.draw.circle(surf, (20, 22, 26), (cx, cy), radius)
    f = pygame.font.Font(None, int(16 * zoom) if zoom >= 0.5 else 14)
    text = f.render(letter, True, (245, 245, 245))
    surf.blit(text, text.get_rect(center=(cx, cy)))


UNITS = [
    ("infantry", "I", "circle", "allies"),
    ("tank", "T", "square", "axis"),
    ("mg", "G", "double_dot", "allies"),
    ("gun", "A", "triangle", "axis"),
]

STYLES = ["badge", "letter", "both"]

for row, zoom in enumerate((1.0, 0.6)):
    y0 = 120 + row * 250
    for col, style in enumerate(STYLES):
        x0 = 90 + col * 330
        for i, (kind, letter, shape, faction) in enumerate(UNITS):
            cx = x0 + i * 80
            cy = y0
            draw_base(surface, cx, cy, faction, zoom)
            draw_sprite_body(surface, cx, cy, kind, zoom)
            if style in ("badge", "both"):
                draw_badge(surface, cx, cy, shape, zoom)
            if style in ("letter", "both"):
                draw_letter(surface, cx, cy, letter, zoom)

for col, name in enumerate(("Current: shape badge", "Letter in center", "Letter + badge")):
    surface.blit(font.render(name, True, (230, 230, 230)), (90 + col * 330, 60))
for row, name in enumerate(("zoom 1.0", "zoom 0.6")):
    surface.blit(font.render(name, True, (180, 180, 180)), (14, 120 + row * 250 - 8))

out = "/Users/lin/trae_projects/PyCC2/docs/assets/unit_letter_sample.png"
pygame.image.save(surface, out)
print("saved", out)
