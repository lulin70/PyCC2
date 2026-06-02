"""
Achievement Event Bridge - Connects game events to achievement tracking.

Subscribes to EventBus combat/campaign events and triggers
achievement progress updates via AchievementManager.

Integration points:
- CombatResolver publishes UnitAttacked / UnitKilled events
- CampaignSystem publishes BattleWon / CampaignComplete events
- AchievementEventBridge maps events to achievement progress
"""

from typing import Any, Optional, TYPE_CHECKING

from pycc2.domain.systems.achievement_system import (
    AchievementManager,
    AchievementCategory,
)

if TYPE_CHECKING:
    from pycc2.services.event_bus import EventBus


class AchievementEventBridge:
    """Bridges game events to achievement progress tracking."""

    def __init__(self, manager: AchievementManager):
        self._manager = manager
        self._battle_casualties: int = 0
        self._battle_kills: int = 0
        self._battle_damage_taken: int = 0
        self._consecutive_flawless: int = 0
        self._battles_won: int = 0
        self._sniper_kills: int = 0
        self._tank_kills: int = 0

    def subscribe(self, event_bus: "EventBus") -> None:
        """Subscribe to game events from EventBus."""
        event_bus.subscribe("UnitAttacked", self._on_unit_attacked)
        event_bus.subscribe("UnitKilled", self._on_unit_killed)
        event_bus.subscribe("BattleWon", self._on_battle_won)
        event_bus.subscribe("CampaignComplete", self._on_campaign_complete)

    def _on_unit_attacked(self, event: dict) -> None:
        """Track damage taken by player units."""
        target_faction = event.get("target_faction", "")
        if target_faction == "ALLIES":
            damage = event.get("damage", 0)
            self._battle_damage_taken += int(damage)

    def _on_unit_killed(self, event: dict) -> None:
        """Track kills and trigger achievement progress."""
        killed_faction = event.get("faction", "")
        killer_role = event.get("attacker_role", "")
        killed_unit_type = event.get("unit_type", "")

        if killed_faction == "AXIS":
            self._battle_kills += 1

            self._manager.add_progress("first_blood", 1)

            if killer_role == "sniper":
                self._sniper_kills += 1
                self._manager.set_progress("sharpshooter", self._sniper_kills)

            if killed_unit_type in ("tank", "vehicle"):
                self._tank_kills += 1
                self._manager.set_progress("tank_buster", self._tank_kills)

        elif killed_faction == "ALLIES":
            self._battle_casualties += 1

    def _on_battle_won(self, event: dict) -> None:
        """Track battle victories and check survival achievements."""
        self._battles_won += 1
        self._manager.set_progress("commander", self._battles_won)

        if self._battle_casualties == 0:
            self._manager.add_progress("zero_casualties", 1)

        if self._battle_damage_taken == 0:
            self._consecutive_flawless += 1
            self._manager.set_progress("flawless", self._consecutive_flawless)
        else:
            self._consecutive_flawless = 0

        battle_duration = event.get("duration_seconds", 0)
        if battle_duration > 0 and battle_duration < 120:
            self._manager.add_progress("blitzkrieg", 1)

        if self._battle_kills > 0:
            critical_health_units = event.get("critical_health_units", 0)
            if critical_health_units > 0:
                self._manager.add_progress("survivor", 1)

        self._reset_battle_stats()

    def _on_campaign_complete(self, event: dict) -> None:
        """Handle campaign completion."""
        campaign_name = event.get("campaign", "")
        if campaign_name == "market_garden":
            self._manager.add_progress("market_garden", 1)

        turns_held = event.get("arnhem_bridge_turns_held", 0)
        if turns_held > 0:
            self._manager.set_progress("bridge_too_far", turns_held)

    def _reset_battle_stats(self) -> None:
        """Reset per-battle tracking after battle ends."""
        self._battle_casualties = 0
        self._battle_kills = 0
        self._battle_damage_taken = 0
