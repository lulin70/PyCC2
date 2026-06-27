"""Combat Camera Controller - Bridges combat events to camera effects.

Subscribes to EventBus combat events and triggers appropriate
camera effects via EffectStack on the Camera.

Integration points:
- CombatResolver publishes UnitAttacked / UnitKilled events
- CombatCameraController subscribes and maps to camera effects
- EffectStack on Camera executes the visual effects
"""

from typing import TYPE_CHECKING, Any, Optional

from pycc2.domain.interfaces import IEventPublisher
from pycc2.presentation.rendering.camera_effects import (
    EffectStack,
    create_push_pull,
    create_screen_freeze,
    create_shake,
    create_slow_motion,
    create_zoom_impact,
)

if TYPE_CHECKING:
    from pycc2.domain.interfaces.camera_protocol import ICamera


class CombatCameraController:
    """Maps combat events to cinematic camera effects."""

    def __init__(self, camera: Optional["ICamera"] = None):
        self._camera = camera
        self._effect_stack: EffectStack | None = None
        self._enabled = True
        self._kill_count = 0

    def set_camera(self, camera: "ICamera") -> None:
        self._camera = camera

    def set_effect_stack(self, stack: EffectStack) -> None:
        self._effect_stack = stack

    def set_enabled(self, enabled: bool) -> None:
        self._enabled = enabled

    def subscribe(self, event_bus: IEventPublisher) -> None:
        """Subscribe to combat events from EventBus."""
        event_bus.subscribe_to("UnitAttacked", self._on_unit_attacked)
        event_bus.subscribe_to("UnitKilled", self._on_unit_killed)
        event_bus.subscribe_to("BattleWon", self._on_battle_won)
        event_bus.subscribe_to("Explosion", self._on_explosion)

    def _push(self, effect: Any) -> None:
        if not self._enabled or self._effect_stack is None:
            return
        self._effect_stack.push(effect)

    def _on_unit_attacked(self, event: dict) -> None:
        """Handle unit attacked event - light shake."""
        damage = event.get("damage", 0)
        if damage >= 50:
            self._push(create_shake(intensity=4.0, duration=0.15))
            self._push(create_zoom_impact(zoom_factor=0.9, duration=0.1, recover=0.3))
        elif damage >= 20:
            self._push(create_shake(intensity=2.5, duration=0.1))
        else:
            self._push(create_shake(intensity=1.0, duration=0.08))

    def _on_unit_killed(self, event: dict) -> None:
        """Handle unit killed event - stronger effects."""
        self._kill_count += 1
        faction = event.get("faction", "")

        if faction == "AXIS":
            self._push(create_shake(intensity=5.0, duration=0.2))
            self._push(create_zoom_impact(zoom_factor=0.8, duration=0.12, recover=0.4))
            if self._kill_count <= 3:
                self._push(create_slow_motion(time_scale=0.4, duration=0.8))
        else:
            self._push(create_shake(intensity=3.0, duration=0.15))

    def _on_battle_won(self, event: dict) -> None:
        """Handle battle victory - dramatic freeze."""
        self._push(create_screen_freeze(duration=0.4))
        self._push(create_push_pull(distance=25.0, duration=0.6))

    def _on_explosion(self, event: dict) -> None:
        """Handle explosion event - heavy effects."""
        intensity = event.get("intensity", 1.0)

        if intensity >= 3.0:
            self._push(create_shake(intensity=8.0, duration=0.3))
            self._push(create_zoom_impact(zoom_factor=0.7, duration=0.15, recover=0.5))
            self._push(create_push_pull(distance=40.0, duration=0.5))
        elif intensity >= 1.5:
            self._push(create_shake(intensity=5.0, duration=0.2))
            self._push(create_zoom_impact(zoom_factor=0.85, duration=0.1, recover=0.3))
        else:
            self._push(create_shake(intensity=3.0, duration=0.12))

    def reset_kill_count(self) -> None:
        self._kill_count = 0
