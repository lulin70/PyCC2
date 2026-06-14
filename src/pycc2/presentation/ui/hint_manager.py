from __future__ import annotations
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pygame

@dataclass(slots=True)
class ActiveHint:
    text: str
    x: float
    y: float
    lifetime: int
    max_lifetime: int

class HintManager:
    
    HINT_COOLDOWN: int = 300
    
    def __init__(self):
        self._hints: list[ActiveHint] = []
        self._global_cooldown: int = 0
        self._enabled: bool = True
        # Pre-create font to avoid per-frame allocation (lazy init)
        self._font = None
        
    @property
    def enabled(self) -> bool:
        return self._enabled
    
    def _init_font(self) -> None:
        import pygame
        self._font = pygame.font.Font(None, 16)

    def set_enabled(self, val: bool) -> None:
        self._enabled = val
        if not val:
            self._hints.clear()
    
    def show_hint(self, text: str, x: float, y: float, lifetime: int = 180) -> None:
        if not self._enabled:
            return
        self._hints.append(ActiveHint(text=text, x=x, y=y, 
                                      lifetime=lifetime, max_lifetime=lifetime))
    
    def update(self) -> None:
        if self._global_cooldown > 0:
            self._global_cooldown -= 1
        surviving = []
        for h in self._hints:
            h.lifetime -= 1
            if h.lifetime > 0:
                surviving.append(h)
        self._hints = surviving
    
    def render(self, screen) -> None:
        if not self._enabled:
            return
        # Lazy-init font on first render
        if self._font is None:
            import pygame
            self._font = pygame.font.Font(None, 16)
        for h in self._hints:
            alpha = min(255, int(h.lifetime / h.max_lifetime * 255))
            surf = self._font.render(f"💡 {h.text}", True, (255, 255, 200))
            surf.set_alpha(alpha)
            screen.blit(surf, (int(h.x) - surf.get_width() // 2, int(h.y) - 20))

HINTS = {
    "first_select": ("Click on a green unit to select it", 0.0, 0.0),
    "right_click_move": ("Right-click on ground to move selected units", 0.0, 0.0),
    "right_click_attack": ("Right-click on an enemy to attack!", 0.0, 0.0),
    "low_hp": ("Unit is low on HP! Consider retreating.", 0.0, 0.0),
    "out_of_ammo": ("Out of ammunition! Unit will reload automatically.", 0.0, 0.0),
    "enemy_commander_spotted": ("Enemy Commander spotted! High value target!", 0.0, 0.0),
}
