"""SVG Sprite Loader — converts unit-sprite SVGs to pygame Surfaces.

Parses the CC2-style SVG sprites (docs/assets/unit-sprites/) and renders them
as pygame Surfaces using only stdlib (xml.etree.ElementTree) + pygame.draw.

Supported SVG elements:
    - ellipse → pygame.draw.ellipse (body, helmet, shadow)
    - rect    → pygame.draw.rect (boots, gun parts, ammo box)
    - line    → pygame.draw.line (rifle barrel, MG barrel, bipod)
    - circle  → pygame.draw.circle (animation frame markers)

Color formats:
    - #RRGGBB       → (R, G, B, 255)
    - rgba(R,G,B,A) → (R, G, B, A * 255)

Design:
    - Zero external dependencies (only xml.etree + pygame)
    - Pre-caches all 17 SVGs at init time
    - Generates 8-direction rotations from base sprites
    - Falls back gracefully for unsupported elements

Created: 2026-06-19 — P0 UI alignment with docs/assets/unit-sprites/
"""

from __future__ import annotations

import logging
import math
import re
from pathlib import Path
from typing import TYPE_CHECKING

import pygame
from pygame import Surface

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

# Default sprite source directory (relative to project root)
# Path: src/pycc2/presentation/rendering/svg_sprite_loader.py → PyCC2/docs/assets/unit-sprites/
_DEFAULT_SVG_ROOT = (
    Path(__file__).resolve().parent.parent.parent.parent.parent / "docs" / "assets" / "unit-sprites"
)

# Sprite catalog: maps (faction, posture, animation_frame) → filename
SPRITE_CATALOG: dict[tuple[str, str, int | None], str] = {
    # --- Allies ---
    ("allies", "standing", None): "allies/rifleman-standing.svg",
    ("allies", "kneeling", None): "allies/rifleman-kneeling.svg",
    ("allies", "prone", None): "allies/rifleman-prone.svg",
    ("allies", "prone", 0): "allies/rifleman-prone-f0.svg",
    ("allies", "prone", 1): "allies/rifleman-prone-f1.svg",
    ("allies", "prone", 2): "allies/rifleman-prone-f2.svg",
    ("allies", "prone", 3): "allies/rifleman-prone-f3.svg",
    ("allies", "mg_deployed", None): "allies/mg-deployed.svg",
    # --- Axis ---
    ("axis", "standing", None): "axis/gegner-standing.svg",
    ("axis", "kneeling", None): "axis/gegner-kneeling.svg",
    ("axis", "prone", None): "axis/gegner-prone.svg",
    ("axis", "prone", 0): "axis/gegner-prone-f0.svg",
    ("axis", "prone", 1): "axis/gegner-prone-f1.svg",
    ("axis", "prone", 2): "axis/gegner-prone-f2.svg",
    ("axis", "prone", 3): "axis/gegner-prone-f3.svg",
    ("axis", "mg_deployed", None): "axis/mg42-deployed.svg",
}

# Palette reference (from PALETTE_REFERENCE.svg)
PALETTE = {
    "olive_drab": "#5B6B3A",
    "m1_helmet": "#3D4F24",
    "boots_gear": "#4A3C28",
    "feldgrau": "#4A5040",
    "stahlhelm": "#3A4030",
    "weapon_dark": "#3A3020",
    "axis_weapon": "#2A2418",
    "ammo_box": "#D97706",
    "allies_marker": "#D97706",
    "axis_marker": "#DC2626",
}


def _parse_color(color_str: str) -> tuple[int, int, int, int]:
    """Parse SVG color string to RGBA tuple.

    Supports:
        - '#RRGGBB'      → (R, G, B, 255)
        - 'rgba(R,G,B,A)' → (R, G, B, int(A*255))
        - Named colors from PALETTE (lowercased)
    """
    s = color_str.strip()
    if s.startswith("#"):
        hex_str = s[1:]
        if len(hex_str) == 6:
            r = int(hex_str[0:2], 16)
            g = int(hex_str[2:4], 16)
            b = int(hex_str[4:6], 16)
            return (r, g, b, 255)
    elif s.startswith("rgba"):
        m = re.match(r"rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)", s)
        if m:
            r, g, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
            a = int(float(m.group(4)) * 255)
            return (r, g, b, a)
    elif s.lower() in PALETTE:
        return _parse_color(PALETTE[s.lower()])
    # Fallback: dark gray
    return (80, 80, 80, 255)


def _parse_float(attr: str | None, default: float = 0.0) -> float:
    """Safely parse a float attribute."""
    if attr is None:
        return default
    try:
        return float(attr)
    except (ValueError, TypeError):
        return default


def _parse_ellipse_attrs(elem) -> dict:
    """Parse ellipse/circle attributes into drawing parameters."""
    cx = _parse_float(elem.get("cx"), 0)
    cy = _parse_float(elem.get("cy"), 0)
    rx = abs(_parse_float(elem.get("rx"), 0))
    ry = abs(_parse_float(elem.get("ry"), 0))
    fill = _parse_color(elem.get("fill", "#888"))
    return {"cx": cx, "cy": cy, "rx": rx, "ry": ry, "fill": fill}


def _parse_rect_attrs(elem) -> dict:
    """Parse rect attributes into drawing parameters."""
    x = _parse_float(elem.get("x"), 0)
    y = _parse_float(elem.get("y"), 0)
    w = abs(_parse_float(elem.get("width"), 0))
    h = abs(_parse_float(elem.get("height"), 0))
    rx = _parse_float(elem.get("rx"), 0)  # corner radius
    fill = _parse_color(elem.get("fill", "#888"))
    return {"x": x, "y": y, "w": w, "h": h, "rx": rx, "fill": fill}


def _parse_line_attrs(elem) -> dict:
    """Parse line attributes into drawing parameters."""
    x1 = _parse_float(elem.get("x1"), 0)
    y1 = _parse_float(elem.get("y1"), 0)
    x2 = _parse_float(elem.get("x2"), 0)
    y2 = _parse_float(elem.get("y2"), 0)
    stroke = _parse_color(elem.get("stroke", "#000"))
    width = max(1, int(_parse_float(elem.get("stroke-width"), 1)))
    cap = elem.get("stroke-linecap", "butt")
    return {
        "x1": x1, "y1": y1, "x2": x2, "y2": y2,
        "stroke": stroke, "width": width, "cap": cap,
    }


def _draw_rounded_rect(surface: Surface, rect_params: dict) -> None:
    """Draw a rounded rectangle on surface."""
    r = rect_params
    rect = pygame.Rect(int(r["x"]), int(r["y"]), int(r["w"]), int(r["h"]))
    color = r["fill"][:3]  # RGB only for pygame.draw
    radius = max(0, min(int(r["rx"]), rect.width // 2, rect.height // 2))
    if radius > 0:
        pygame.draw.rect(surface, color, rect, border_radius=radius)
    else:
        pygame.draw.rect(surface, color, rect)


class SVGSpriteLoader:
    """Loads and renders CC2-style SVG unit sprites as pygame Surfaces.

    Usage:
        loader = SVGSpriteLoader()
        sprite = loader.load("allies", "standing")   # Standing rifleman
        sprite = loader.load("axis", "prone", frame=2)  # Prone frame 2
        sprites = loader.load_all()                  # Pre-cache everything
    """

    def __init__(self, svg_root: Path | None = None):
        self.svg_root = Path(svg_root) if svg_root else _DEFAULT_SVG_ROOT
        self._cache: dict[str, Surface] = {}
        self._loaded_count = 0
        self._failed_count = 0

        logger.info(
            "[SVGSpriteLoader] Initialized, root=%s, exists=%s",
            self.svg_root,
            self.svg_root.exists(),
        )

    @property
    def is_available(self) -> bool:
        """Check if SVG assets directory exists and has files."""
        return self.svg_root.exists() and self.svg_root.is_dir() and any(self.svg_root.rglob("*.svg"))

    def load(
        self,
        faction: str,
        posture: str,
        frame: int | None = None,
        target_size: tuple[int, int] | None = None,
    ) -> Surface | None:
        """Load and render a single SVG sprite as pygame Surface.

        Args:
            faction: 'allies' or 'axis'
            posture: 'standing', 'kneeling', 'prone', or 'mg_deployed'
            frame: Animation frame number (0-3 for prone animation), None for base
            target_size: Optional (width, height) to scale output

        Returns:
            pygame.Surface with per-pixel alpha, or None if not found
        """
        key = (faction.lower(), posture.lower(), frame)
        if key not in SPRITE_CATALOG:
            logger.debug("[SVGSpriteLoader] No catalog entry for %s", key)
            return None

        rel_path = SPRITE_CATALOG[key]
        cache_key = f"{faction}_{posture}_f{frame}" if frame is not None else f"{faction}_{posture}"

        # Check cache first
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Load and render SVG
        svg_path = self.svg_root / rel_path
        if not svg_path.exists():
            logger.warning("[SVGSpriteLoader] File not found: %s", svg_path)
            self._failed_count += 1
            return None

        surface = self._render_svg(svg_path, target_size)
        if surface is not None:
            self._cache[cache_key] = surface
            self._loaded_count += 1
            logger.debug("[SVGSpriteLoader] Loaded: %s (%dx%d)", cache_key, surface.get_width(), surface.get_height())
        else:
            self._failed_count += 1

        return surface

    def load_all(self, target_size: tuple[int, int] | None = None) -> dict[str, Surface]:
        """Pre-load and cache all SVG sprites.

        Returns:
            Dict mapping cache_key → Surface
        """
        results = {}
        for (faction, posture, frame), _ in SPRITE_CATALOG.items():
            sprite = self.load(faction, posture, frame, target_size)
            if sprite is not None:
                cache_key = f"{faction}_{posture}_f{frame}" if frame is not None else f"{faction}_{posture}"
                results[cache_key] = sprite

        logger.info(
            "[SVGSpriteLoader] load_all complete: %d loaded, %d failed, total=%d",
            self._loaded_count,
            self._failed_count,
            len(SPRITE_CATALOG),
        )
        return results

    def get_rotated(self, surface: Surface, direction: int) -> Surface:
        """Rotate base sprite to face given direction (0-7, where 0=North).

        Direction mapping:
            0=N, 1=NE, 2=E, 3=SE, 4=S, 5=SW, 6=W, 7=NW
        """
        # Each direction step = 45 degrees clockwise
        angle = direction * 45
        return pygame.transform.rotate(surface, angle)

    def _render_svg(
        self,
        svg_path: Path,
        target_size: tuple[int, int] | None = None,
    ) -> Surface | None:
        """Parse SVG file and render to pygame Surface.

        Rendering pipeline:
            1. Parse SVG root element for viewBox/width/height
            2. Create transparent RGBA surface
            3. Draw each element in document order (painters algorithm)
            4. Scale to target_size if specified
        """
        import xml.etree.ElementTree as ET

        try:
            tree = ET.parse(str(svg_path))
        except ET.ParseError as e:
            logger.error("[SVGSpriteLoader] Parse error in %s: %s", svg_path, e)
            return None

        root = tree.getroot()
        ns = {"svg": "http://www.w3.org/2000/svg"}

        # Get dimensions from viewBox or width/height attrs
        vb = root.get("viewBox")
        if vb:
            parts = [float(x) for x in vb.split()]
            # viewBox="min_x min_y width height"
            vw, vh = int(parts[2]), int(parts[3])
        else:
            vw = int(_parse_float(root.get("width"), 32))
            vh = int(_parse_float(root.get("height"), 32))

        # Create transparent surface
        surface = pygame.Surface((vw, vh), flags=pygame.SRCALPHA)
        surface.fill((0, 0, 0, 0))

        # Render each child element
        for elem in root:
            tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag

            try:
                if tag == "ellipse":
                    self._draw_ellipse(surface, elem)
                elif tag == "circle":
                    self._draw_circle(surface, elem)
                elif tag == "rect":
                    self._draw_rect(surface, elem)
                elif tag == "line":
                    self._draw_line(surface, elem)
                elif tag in ("defs", "g", "path", "text", "title", "desc"):
                    pass  # Skip non-rendering elements
                else:
                    logger.debug("[SVGSpriteLoader] Skipping unsupported <%s>", tag)
            except Exception as e:
                logger.warning("[SVGSpriteLoader] Error rendering <%s> in %s: %s", tag, svg_path.name, e)

        # Scale if requested
        if target_size is not None and (vw, vh) != target_size:
            tw, th = target_size
            scaled = pygame.transform.smoothscale(surface, (tw, th))
            return scaled

        return surface

    # ====== Element renderers ======

    def _draw_ellipse(self, surface: Surface, elem) -> None:
        """Render <ellipse> element."""
        p = _parse_ellipse_attrs(elem)
        if p["rx"] <= 0 or p["ry"] <= 0:
            return
        bounds = (
            int(p["cx"] - p["rx"]),
            int(p["cy"] - p["ry"]),
            int(p["rx"] * 2),
            int(p["ry"] * 2),
        )
        color = p["fill"]
        if color[3] < 255:  # Has alpha
            # For alpha ellipses, we need a temporary surface
            temp = pygame.Surface((bounds[2] + 4, bounds[3] + 4), flags=pygame.SRCALPHA)
            temp.fill((0, 0, 0, 0))
            pygame.draw.ellipse(temp, color, (2, 2, bounds[2], bounds[3]))
            surface.blit(temp, (bounds[0] - 2, bounds[1] - 2))
        else:
            pygame.draw.ellipse(surface, color[:3], bounds)

    def _draw_circle(self, surface: Surface, elem) -> None:
        """Render <circle> element (treated as ellipse with equal radii)."""
        cx = _parse_float(elem.get("cx"), 0)
        cy = _parse_float(elem.get("cy"), 0)
        r = abs(_parse_float(elem.get("r"), 0))
        if r <= 0:
            return
        fill = _parse_color(elem.get("fill", "#888"))
        pygame.draw.circle(surface, fill[:3], (int(cx), int(cy)), int(r))

    def _draw_rect(self, surface: Surface, elem) -> None:
        """Render <rect> element with optional rounded corners."""
        p = _parse_rect_attrs(elem)
        if p["w"] <= 0 or p["h"] <= 0:
            return
        _draw_rounded_rect(surface, p)

    def _draw_line(self, surface: Surface, elem) -> None:
        """Render <line> element with optional round caps."""
        p = _parse_line_attrs(elem)
        color = p["stroke"][:3]
        start = (int(p["x1"]), int(p["y1"]))
        end = (int(p["x2"]), int(p["y2"]))
        if p["cap"] == "round":
            pygame.draw.line(surface, color, start, end, width=p["width"])
            # Draw round caps
            pygame.draw.circle(surface, color, start, p["width"] // 2)
            pygame.draw.circle(surface, color, end, p["width"] // 2)
        else:
            pygame.draw.line(surface, color, start, end, width=p["width"])

    # ====== Query API ======

    @property
    def stats(self) -> dict:
        """Return loading statistics."""
        return {
            "loaded": self._loaded_count,
            "failed": self._failed_count,
            "total_catalog": len(SPRITE_CATALOG),
            "cache_size": len(self._cache),
            "available": self.is_available,
        }

    def list_available(self) -> list[str]:
        """List all available sprite keys."""
        return sorted(self._cache.keys())
