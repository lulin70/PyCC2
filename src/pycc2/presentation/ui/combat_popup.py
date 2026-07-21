"""Floating combat text popups for CC2-style battlefield feedback."""

from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import pygame

if TYPE_CHECKING:
    from pycc2.domain.value_objects.damage import Damage, DamageType


# ---------------------------------------------------------------------------
# V-13 (Wave D6) constants
# ---------------------------------------------------------------------------

# Damage number display constraints (Wave B-rev spec)
MAX_DAMAGE_NUMBERS: int = 10  # Max simultaneous damage popups (FIFO eviction)
DAMAGE_NUMBER_THROTTLE_MS: float = 200.0  # Same-unit throttle window
DAMAGE_NUMBER_LIFETIME_MS: float = 1200.0  # 1.2s display duration
DAMAGE_NUMBER_FONT_SIZE_NORMAL: int = 18
DAMAGE_NUMBER_FONT_SIZE_CRITICAL: int = 24

# Color coding by damage type (Wave B-rev spec)
DAMAGE_COLOR_CRITICAL: tuple[int, int, int] = (255, 80, 80)  # Crit: red
DAMAGE_COLOR_EXPLOSIVE: tuple[int, int, int] = (255, 150, 30)  # Explosion: orange
DAMAGE_COLOR_INCENDIARY: tuple[int, int, int] = (255, 200, 50)  # Fire: yellow
DAMAGE_COLOR_KINETIC: tuple[int, int, int] = (255, 255, 255)  # Bullet: white
DAMAGE_COLOR_DEFAULT: tuple[int, int, int] = (220, 220, 220)  # Default: light gray


@dataclass
class CombatPopup:
    """A single floating text popup."""

    text: str
    x: float
    y: float
    color: tuple[int, int, int]
    created_at: float = field(default_factory=time.time)
    duration: float = 2.0
    # V-13 (Wave D6): damage number metadata
    is_damage_number: bool = False
    damage_amount: float = 0.0
    damage_type_name: str | None = None
    font_size: int = 13  # V-13: allow custom font size for crits

    @property
    def age(self) -> float:
        """Get the age."""
        return time.time() - self.created_at

    @property
    def is_expired(self) -> bool:
        """Get the is expired."""
        return self.age > self.duration

    @property
    def alpha(self) -> int:
        """Fade out in last 0.5 seconds."""
        remaining = self.duration - self.age
        if remaining < 0.5:
            return int(255 * remaining / 0.5)
        return 255

    @property
    def offset_y(self) -> float:
        """Float upward over time."""
        return -self.age * 15  # 15 pixels per second upward


class CombatPopupManager:
    """Manages floating combat text popups."""

    def __init__(self, max_popups: int = 20):
        """Initialize the CombatPopupManager."""
        self._popups: deque[CombatPopup] = deque()
        self._max_popups = max_popups
        self._font: pygame.font.Font | None = None
        # V-13 (Wave D6): separate font cache for damage numbers (different sizes)
        self._damage_fonts: dict[int, pygame.font.Font] = {}
        # V-13 (Wave D6): per-unit throttle tracking (unit_id → last shown timestamp)
        self._last_damage_shown: dict[str, float] = {}
        # Surface pool for popup alpha surfaces
        self._surface_pool: dict[tuple[int, int], pygame.Surface] = {}

    def add_popup(
        self,
        text: str,
        world_x: float,
        world_y: float,
        color: tuple[int, int, int] = (255, 255, 100),
    ) -> None:
        """Add a new combat popup."""
        if self._font is None:
            from pycc2.presentation.ui.font_helper import safe_init_font

            self._font = safe_init_font(13, bold=True)

        self._popups.append(CombatPopup(text=text, x=world_x, y=world_y, color=color))

        # Remove oldest if too many
        if len(self._popups) > self._max_popups:
            self._popups.popleft()

    def add_taking_fire(self, x: float, y: float) -> None:
        """Add taking fire."""
        self.add_popup("Taking fire!", x, y, (255, 100, 100))

    def add_breaking(self, x: float, y: float) -> None:
        """Add breaking."""
        self.add_popup("They're breaking!", x, y, (255, 200, 100))

    def add_pinned(self, x: float, y: float) -> None:
        """Add pinned."""
        self.add_popup("Pinned!", x, y, (255, 150, 50))

    def add_out_of_ammo(self, x: float, y: float) -> None:
        """Add out of ammo."""
        self.add_popup("Out of ammo!", x, y, (200, 200, 200))

    def add_kia(self, x: float, y: float) -> None:
        """Add kia."""
        self.add_popup("KIA", x, y, (255, 50, 50))

    def add_surrender(self, x: float, y: float) -> None:
        """Add surrender."""
        self.add_popup("Surrender!", x, y, (200, 200, 100))

    # ----------------------------------------------------------------------
    # V-13 (Wave D6): Damage number display
    # ----------------------------------------------------------------------

    def add_damage_number(
        self,
        target_position: tuple[float, float],
        damage: Damage,
        is_critical: bool | None = None,
        unit_id: str | None = None,
    ) -> bool:
        """Display damage number at target position (V-13 Wave D6).

        Shows a floating "-N" damage value above the hit unit with color
        coding by damage type and larger font for critical hits.

        Constraints (Wave B-rev spec):
        - Max 10 simultaneous damage numbers (FIFO eviction)
        - Same unit throttled to 1 display per 200ms (avoid stacking)
        - Critical hits (damage.amount >= 75) use larger font + red color

        Args:
            target_position: (x, y) world coordinates of hit unit.
            damage: Damage value object with amount + type.
            is_critical: Override critical detection. If None, uses damage.is_critical.
            unit_id: Optional unit ID for throttle tracking. If None, no throttle.

        Returns:
            True if damage number was displayed, False if throttled/suppressed.
        """
        # Resolve critical flag (default to damage.is_critical property)
        if is_critical is None:
            is_critical = damage.is_critical

        # Throttle: same unit within 200ms → suppress
        if unit_id is not None:
            now = time.time()
            if unit_id in self._last_damage_shown:
                last_shown = self._last_damage_shown[unit_id]
                if (now - last_shown) * 1000.0 < DAMAGE_NUMBER_THROTTLE_MS:
                    return False
            self._last_damage_shown[unit_id] = now

        # Get color + font size
        color = _get_damage_color(damage.damage_type, is_critical)
        font_size = (
            DAMAGE_NUMBER_FONT_SIZE_CRITICAL
            if is_critical
            else DAMAGE_NUMBER_FONT_SIZE_NORMAL
        )

        # Format text: "-25" for normal, "-25!" for critical
        text = f"-{int(damage.amount)}"
        if is_critical:
            text += "!"

        # Append damage-number popup
        popup = CombatPopup(
            text=text,
            x=target_position[0],
            y=target_position[1],
            color=color,
            duration=DAMAGE_NUMBER_LIFETIME_MS / 1000.0,  # Convert ms → s
            is_damage_number=True,
            damage_amount=damage.amount,
            damage_type_name=damage.damage_type.name,
            font_size=font_size,
        )
        self._popups.append(popup)

        # FIFO eviction: limit damage numbers specifically (not all popups)
        damage_popups = [p for p in self._popups if p.is_damage_number]
        if len(damage_popups) > MAX_DAMAGE_NUMBERS:
            # Remove oldest damage popup
            for p in list(self._popups):
                if p.is_damage_number:
                    self._popups.remove(p)
                    break

        # Also enforce overall max_popups
        while len(self._popups) > self._max_popups:
            self._popups.popleft()

        return True

    def render(self, surface: pygame.Surface, camera) -> None:
        """Render all active popups."""
        # Remove expired
        self._popups = deque(p for p in self._popups if not p.is_expired)

        if not self._popups:
            return

        cam_x = getattr(camera, "offset_x", 0)
        cam_y = getattr(camera, "offset_y", 0)

        for popup in self._popups:
            # V-13: pick font based on popup type (damage numbers can have custom size)
            font = self._get_font(popup.font_size, is_damage_number=popup.is_damage_number)

            screen_x = popup.x - cam_x
            screen_y = popup.y - cam_y + popup.offset_y

            # Render text with alpha – reuse cached surface
            text_surf = font.render(popup.text, True, popup.color)
            text_size = text_surf.get_size()
            if text_size not in self._surface_pool:
                self._surface_pool[text_size] = pygame.Surface(text_size, pygame.SRCALPHA)
            alpha_surf = self._surface_pool[text_size]
            alpha_surf.fill((0, 0, 0, 0))
            alpha_surf.blit(text_surf, (0, 0))
            alpha_surf.set_alpha(popup.alpha)

            # Draw with shadow for readability – reuse same pool
            shadow_surf = font.render(popup.text, True, (0, 0, 0))
            shadow_size = shadow_surf.get_size()
            if shadow_size not in self._surface_pool:
                self._surface_pool[shadow_size] = pygame.Surface(shadow_size, pygame.SRCALPHA)
            shadow_alpha = self._surface_pool[shadow_size]
            shadow_alpha.fill((0, 0, 0, 0))
            shadow_alpha.blit(shadow_surf, (0, 0))
            shadow_alpha.set_alpha(popup.alpha)

            surface.blit(shadow_alpha, (screen_x + 1, screen_y + 1))
            surface.blit(alpha_surf, (screen_x, screen_y))

    def _get_font(self, size: int, is_damage_number: bool = False) -> pygame.font.Font:
        """Get font, with caching for damage-number sizes (V-13 Wave D6).

        Args:
            size: Font size in points.
            is_damage_number: If True, use damage-number font cache (bold).

        Returns:
            pygame.font.Font instance (fallback to pygame default if SysFont fails).
        """
        if not is_damage_number:
            if self._font is None:
                from pycc2.presentation.ui.font_helper import safe_init_font

                self._font = safe_init_font(13, bold=True) or pygame.font.Font(None, 13)
            return self._font

        # Damage number font (cached by size)
        if size not in self._damage_fonts:
            from pycc2.presentation.ui.font_helper import safe_init_font

            self._damage_fonts[size] = safe_init_font(size, bold=True) or pygame.font.Font(None, size)
        return self._damage_fonts[size]


# ---------------------------------------------------------------------------
# V-13 (Wave D6): Module-private helpers
# ---------------------------------------------------------------------------


def _get_damage_color(
    damage_type: DamageType,
    is_critical: bool,
) -> tuple[int, int, int]:
    """Return color tuple for damage number display (V-13 Wave D6).

    Color coding (Wave B-rev spec):
    - Critical (>=75): red (overrides type color)
    - Explosive: orange
    - Incendiary: yellow
    - Kinetic: white
    - Other: light gray

    Args:
        damage_type: DamageType enum value from Damage.damage_type.
        is_critical: True for critical hits (amount >= 75).

    Returns:
        (R, G, B) tuple in 0-255 range.
    """
    if is_critical:
        return DAMAGE_COLOR_CRITICAL

    # Lazy import to avoid module-level circular dependency
    from pycc2.domain.value_objects.damage import DamageType

    match damage_type:
        case DamageType.EXPLOSIVE:
            return DAMAGE_COLOR_EXPLOSIVE
        case DamageType.INCENDIARY:
            return DAMAGE_COLOR_INCENDIARY
        case DamageType.KINETIC:
            return DAMAGE_COLOR_KINETIC
        case _:
            return DAMAGE_COLOR_DEFAULT
