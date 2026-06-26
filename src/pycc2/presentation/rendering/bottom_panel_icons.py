"""Procedural icon generation for the CC2 bottom panel.

No external assets are required; all command, roster, and portrait icons are
drawn programmatically onto small pygame Surfaces.
"""

from __future__ import annotations

from pygame import Rect, Surface, draw


def create_command_icons(bg_color: tuple[int, int, int]) -> dict[str, Surface]:
    """Create 24x24 command button icons procedurally - enhanced recognizable versions."""
    icons: dict[str, Surface] = {}
    bg = bg_color

    # Move (Z): Boot/footprint icon
    s = Surface((24, 24))
    s.fill(bg)
    green = (80, 220, 80)
    # Boot sole (horizontal rectangle)
    draw.rect(s, green, Rect(6, 14, 12, 5))
    # Boot upper (angled shape)
    draw.polygon(s, green, [(8, 14), (14, 14), (12, 6), (10, 6)])
    # Boot heel
    draw.rect(s, green, Rect(6, 10, 4, 4))
    # Sole tread lines
    draw.line(s, (60, 180, 60), (7, 16), (17, 16), 1)
    draw.line(s, (60, 180, 60), (7, 18), (17, 18), 1)
    icons["move"] = s

    # Fast (X): Running figure with double arrows
    s = Surface((24, 24))
    s.fill(bg)
    bright_green = (100, 255, 100)
    # Running figure - head
    draw.circle(s, bright_green, (10, 4), 3)
    # Body leaning forward
    draw.line(s, bright_green, (10, 7), (12, 14), 2)
    # Arms swinging
    draw.line(s, bright_green, (10, 9), (6, 11), 2)
    draw.line(s, bright_green, (10, 9), (15, 8), 2)
    # Legs in running pose
    draw.line(s, bright_green, (12, 14), (7, 19), 2)
    draw.line(s, bright_green, (12, 14), (17, 19), 2)
    # Speed lines
    draw.line(s, (80, 200, 80), (3, 8), (3, 12), 1)
    draw.line(s, (80, 200, 80), (5, 6), (5, 10), 1)
    # Double arrow indicating speed
    draw.polygon(s, bright_green, [(18, 10), (22, 13), (18, 16)])
    draw.polygon(s, bright_green, [(20, 10), (24, 13), (20, 16)])
    icons["fast"] = s

    # Sneak (S): Crouching figure
    s = Surface((24, 24))
    s.fill(bg)
    olive = (140, 180, 80)
    # Crouching head (lower position)
    draw.circle(s, olive, (8, 10), 3)
    # Crouched body (horizontal)
    draw.line(s, olive, (8, 12), (16, 12), 2)
    # Bent legs
    draw.line(s, olive, (8, 12), (6, 16), 2)
    draw.line(s, olive, (6, 16), (8, 19), 2)
    # Arm reaching forward
    draw.line(s, olive, (14, 12), (19, 10), 2)
    # Stealth dots (quiet movement)
    draw.circle(s, (100, 140, 60), (20, 18), 1)
    draw.circle(s, (100, 140, 60), (22, 16), 1)
    icons["sneak"] = s

    # Attack/Fire (C): Crosshair with center dot
    s = Surface((24, 24))
    s.fill(bg)
    red = (255, 60, 60)
    cx, cy = 12, 12
    # Outer circle
    draw.circle(s, red, (cx, cy), 9, 1)
    # Inner circle
    draw.circle(s, red, (cx, cy), 4, 1)
    # Center dot
    draw.circle(s, red, (cx, cy), 1)
    # Crosshair lines extending beyond circles
    draw.line(s, red, (cx, cy - 11), (cx, cy - 5), 1)
    draw.line(s, red, (cx, cy + 5), (cx, cy + 11), 1)
    draw.line(s, red, (cx - 11, cy), (cx - 5, cy), 1)
    draw.line(s, red, (cx + 5, cy), (cx + 11, cy), 1)
    icons["attack"] = s

    # Smoke (V): Cloud/smoke puff shape
    s = Surface((24, 24))
    s.fill(bg)
    gray = (180, 180, 180)
    dark_gray = (140, 140, 140)
    light_gray = (210, 210, 210)
    # Multiple overlapping circles for cloud effect
    draw.circle(s, gray, (8, 15), 5)
    draw.circle(s, light_gray, (14, 13), 6)
    draw.circle(s, dark_gray, (11, 9), 5)
    draw.circle(s, gray, (6, 11), 4)
    draw.circle(s, light_gray, (18, 11), 3)
    # Wispy top
    draw.circle(s, dark_gray, (13, 6), 3)
    # Base line (ground)
    draw.line(s, (100, 100, 100), (3, 20), (21, 20), 1)
    icons["smoke"] = s

    # Defend (D): Shield with horizontal line
    s = Surface((24, 24))
    s.fill(bg)
    shield_color = (100, 160, 255)
    shield_dark = (50, 80, 140)
    # Shield outline (wider shape)
    shield_pts = [(12, 1), (22, 6), (22, 14), (12, 22), (2, 14), (2, 6)]
    draw.polygon(s, shield_color, shield_pts)
    # Inner fill
    inner_pts = [(12, 4), (19, 8), (19, 13), (12, 19), (5, 13), (5, 8)]
    draw.polygon(s, shield_dark, inner_pts)
    # Chevron (V-shape pointing up) on shield
    draw.polygon(s, (200, 220, 255), [(7, 7), (12, 13), (17, 7)])
    draw.polygon(s, (200, 220, 255), [(7, 7), (12, 13), (17, 7)], 1)
    # Shield border
    draw.polygon(s, (140, 190, 255), shield_pts, 1)
    icons["defend"] = s

    # Cancel: Red X
    s = Surface((24, 24))
    s.fill(bg)
    x_red = (255, 50, 50)
    draw.line(s, x_red, (5, 5), (19, 19), 3)
    draw.line(s, x_red, (19, 5), (5, 19), 3)
    icons["cancel"] = s

    # End battle: Olive flag on pole
    s = Surface((24, 24))
    s.fill(bg)
    olive = (120, 140, 80)
    # Pole
    draw.line(s, (180, 170, 140), (6, 3), (6, 21), 2)
    # Flag (waving)
    draw.polygon(s, olive, [(7, 3), (20, 5), (19, 13), (7, 11)])
    # Border on flag
    draw.polygon(s, (80, 100, 50), [(7, 3), (20, 5), (19, 13), (7, 11)], 1)
    icons["end_battle"] = s

    # Hide (H): Eye with slash
    s = Surface((24, 24))
    s.fill(bg)
    eye_color = (180, 200, 220)
    # Eye outline (almond shape)
    eye_pts = [(2, 12), (6, 7), (12, 6), (18, 7), (22, 12), (18, 17), (12, 18), (6, 17)]
    draw.polygon(s, eye_color, eye_pts, 2)
    # Pupil
    draw.circle(s, (100, 150, 200), (12, 12), 3)
    draw.circle(s, (40, 40, 40), (12, 12), 1)
    # Slash through eye
    draw.line(s, (255, 60, 60), (4, 4), (20, 20), 2)
    icons["hide"] = s

    return icons


def create_roster_icons(bg_color: tuple[int, int, int]) -> dict[str, Surface]:
    """Create 16x16 unit type thumbnail icons procedurally - visually distinct per unit type."""
    icons: dict[str, Surface] = {}
    bg = bg_color

    # Infantry: Soldier silhouette (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    green = (80, 200, 80)
    dark_green = (50, 150, 50)
    # Helmet (semi-circle)
    draw.ellipse(s, dark_green, (5, 1, 6, 4))
    # Helmet brim
    draw.line(s, dark_green, (4, 4), (12, 4), 1)
    # Face
    draw.rect(s, (200, 170, 140), (6, 4, 4, 2))
    # Body/torso
    draw.rect(s, green, (5, 6, 6, 5))
    # Arms
    draw.line(s, green, (5, 7), (3, 9), 1)
    draw.line(s, green, (10, 7), (12, 9), 1)
    # Legs
    draw.line(s, dark_green, (6, 11), (5, 14), 2)
    draw.line(s, dark_green, (9, 11), (10, 14), 2)
    # Boots
    draw.rect(s, (45, 38, 28), (4, 13, 2, 2))
    draw.rect(s, (45, 38, 28), (9, 13, 2, 2))
    # Rifle
    draw.line(s, (60, 60, 60), (11, 6), (14, 3), 1)
    icons["infantry"] = s

    # MG: Gun shape (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    mg_green = (80, 200, 80)
    mg_yellow = (200, 200, 80)
    # Gunner silhouette (small)
    draw.circle(s, mg_green, (5, 4), 2)
    draw.rect(s, mg_green, (4, 6, 3, 4))
    # MG barrel (thick horizontal line)
    draw.line(s, mg_yellow, (7, 7), (15, 5), 2)
    # MG body
    draw.rect(s, (100, 100, 60), (7, 6, 4, 3))
    # Bipod legs
    draw.line(s, (80, 80, 50), (13, 6), (14, 10), 1)
    draw.line(s, (80, 80, 50), (15, 5), (15, 10), 1)
    # Ammo belt
    draw.rect(s, (55, 50, 38), (3, 8, 3, 2))
    icons["mg"] = s

    # Sniper: Soldier with long rifle (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    green = (80, 200, 80)
    dark_green = (50, 150, 50)
    # Helmet (semi-circle)
    draw.ellipse(s, dark_green, (4, 0, 6, 4))
    draw.line(s, dark_green, (3, 3), (11, 3), 1)
    # Face
    draw.rect(s, (200, 170, 140), (5, 3, 4, 2))
    # Body/torso (slightly hunched)
    draw.rect(s, green, (4, 5, 6, 4))
    # Arms - one forward holding rifle
    draw.line(s, green, (4, 6), (2, 8), 1)
    draw.line(s, green, (9, 6), (11, 5), 1)
    # Long rifle extending far forward
    draw.line(s, (60, 60, 60), (11, 5), (15, 1), 1)
    # Scope on rifle
    draw.rect(s, (100, 180, 255), (12, 3, 3, 2))
    # Legs (kneeling/prone)
    draw.line(s, dark_green, (5, 9), (4, 12), 2)
    draw.line(s, dark_green, (8, 9), (10, 12), 2)
    # Boots
    draw.rect(s, (45, 38, 28), (3, 11, 2, 2))
    draw.rect(s, (45, 38, 28), (9, 11, 2, 2))
    icons["sniper"] = s

    # Commander: Soldier with radio antenna (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    green = (80, 200, 80)
    dark_green = (50, 150, 50)
    gold = (255, 230, 80)
    # Officer cap (flat top with brim)
    draw.rect(s, dark_green, (4, 0, 7, 3))
    draw.line(s, dark_green, (3, 3), (12, 3), 1)
    # Cap badge (small gold dot)
    draw.rect(s, gold, (7, 1, 2, 1))
    # Face
    draw.rect(s, (200, 170, 140), (5, 3, 4, 2))
    # Body/torso
    draw.rect(s, green, (4, 5, 6, 5))
    # Arms - one raised holding radio
    draw.line(s, green, (4, 6), (2, 8), 1)
    draw.line(s, green, (9, 6), (12, 4), 1)
    # Radio backpack
    draw.rect(s, (70, 70, 80), (10, 4, 4, 5))
    # Radio antenna (tall line from backpack)
    draw.line(s, (180, 180, 190), (12, 4), (12, 0), 1)
    # Antenna tip
    draw.circle(s, (255, 230, 80), (12, 0), 1)
    # Legs
    draw.line(s, dark_green, (5, 10), (5, 13), 2)
    draw.line(s, dark_green, (8, 10), (9, 13), 2)
    # Boots
    draw.rect(s, (45, 38, 28), (4, 12, 2, 2))
    draw.rect(s, (45, 38, 28), (8, 12, 2, 2))
    icons["commander"] = s

    # Engineer: Wrench (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    wrench_silver = (180, 180, 190)
    wrench_dark = (120, 120, 130)
    # Wrench handle (diagonal)
    draw.line(s, wrench_dark, (3, 13), (10, 6), 2)
    # Wrench head (open end)
    draw.line(s, wrench_silver, (8, 4), (10, 6), 2)
    draw.line(s, wrench_silver, (10, 6), (12, 4), 2)
    draw.line(s, wrench_silver, (8, 4), (9, 3), 1)
    draw.line(s, wrench_silver, (12, 4), (13, 3), 1)
    # Small figure
    draw.circle(s, (80, 200, 80), (4, 3), 2)
    draw.line(s, (80, 200, 80), (4, 5), (4, 8), 1)
    icons["engineer"] = s

    # AT: Rocket shape (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    rocket_red = (200, 80, 60)
    rocket_dark = (150, 50, 40)
    # Rocket body (horizontal)
    draw.rect(s, rocket_red, (2, 6, 10, 4))
    # Nose cone
    draw.polygon(s, rocket_dark, [(12, 6), (15, 8), (12, 10)])
    # Fins
    draw.polygon(s, rocket_dark, [(2, 6), (4, 3), (5, 6)])
    draw.polygon(s, rocket_dark, [(2, 10), (4, 13), (5, 10)])
    # Exhaust flame
    draw.line(s, (255, 200, 50), (1, 8), (0, 7), 1)
    draw.line(s, (255, 200, 50), (1, 8), (0, 9), 1)
    icons["at"] = s

    # Mortar: Tube shape (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    tube_gray = (140, 140, 150)
    tube_dark = (100, 100, 110)
    # Tube (angled)
    draw.line(s, tube_gray, (4, 14), (10, 4), 3)
    # Muzzle opening
    draw.circle(s, tube_dark, (10, 4), 2)
    # Base plate
    draw.rect(s, tube_dark, (2, 13, 4, 2))
    # Bipod
    draw.line(s, tube_dark, (6, 10), (3, 12), 1)
    draw.line(s, tube_dark, (6, 10), (8, 13), 1)
    icons["mortar"] = s

    # Tank: Gray rectangle with turret (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    tank_gray = (160, 160, 170)
    tank_dark = (120, 120, 130)
    # Hull
    draw.rect(s, tank_gray, (2, 8, 12, 5))
    # Turret
    draw.rect(s, tank_dark, (4, 5, 6, 4))
    # Barrel
    draw.line(s, (100, 100, 110), (10, 7), (15, 5), 2)
    # Tracks
    draw.rect(s, (80, 80, 90), (1, 12, 14, 2))
    # Track details
    for tx in range(2, 14, 3):
        draw.line(s, (60, 60, 70), (tx, 12), (tx, 14), 1)
    icons["tank"] = s

    # Medic: White cross on green (16x16)
    s = Surface((16, 16))
    s.fill(bg)
    white = (240, 240, 240)
    green_bg = (60, 120, 60)
    # Green background circle
    draw.circle(s, green_bg, (8, 8), 6)
    # White cross
    draw.rect(s, white, (6, 3, 4, 10))  # vertical bar
    draw.rect(s, white, (3, 6, 10, 4))  # horizontal bar
    icons["medic"] = s

    return icons


def create_commander_portrait(
    bg_color: tuple[int, int, int], border_color: tuple[int, int, int]
) -> Surface:
    """Create 24x24 commander portrait - pixel art face with beret/cap."""
    s = Surface((24, 24))
    bg = bg_color
    s.fill(bg)
    skin = (210, 180, 150)
    skin_dark = (185, 155, 125)
    beret = (50, 80, 50)
    beret_dark = (35, 55, 35)
    eye_color = (40, 40, 40)
    lip = (180, 130, 120)

    # Beret (flat cap tilted to one side)
    draw.ellipse(s, beret, (4, 1, 16, 6))
    # Beret band
    draw.rect(s, beret_dark, (5, 5, 14, 2))
    # Beret badge (small gold circle)
    draw.circle(s, (255, 230, 80), (8, 3), 1)

    # Face (oval)
    draw.ellipse(s, skin, (6, 5, 12, 12))
    # Face shadow on right side
    draw.ellipse(s, skin_dark, (13, 7, 4, 8))

    # Eyes (two small dots)
    draw.rect(s, eye_color, (8, 9, 2, 2))
    draw.rect(s, eye_color, (14, 9, 2, 2))
    # Eye whites (tiny highlight)
    draw.rect(s, (240, 240, 240), (8, 9, 1, 1))
    draw.rect(s, (240, 240, 240), (14, 9, 1, 1))

    # Nose (small line)
    draw.line(s, skin_dark, (11, 10), (11, 13), 1)

    # Mouth
    draw.line(s, lip, (9, 15), (13, 15), 1)

    # Collar/shoulders
    draw.rect(s, beret_dark, (4, 17, 16, 3))
    # Collar V-neck
    draw.polygon(s, skin, [(10, 17), (12, 17), (11, 20)])

    # Rank insignia on collar (small gold bars)
    draw.rect(s, (255, 230, 80), (5, 17, 3, 1))
    draw.rect(s, (255, 230, 80), (16, 17, 3, 1))

    # Border
    draw.rect(s, border_color, (0, 0, 24, 24), 1)

    return s
