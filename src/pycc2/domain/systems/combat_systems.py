"""Combat-related domain systems: FriendlyFireSystem (C9), RicochetSystem (D8)."""

from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class FriendlyFireSystem:
    """
    Friendly fire detection and penalty system.

    Checks if attack line passes through friendly units.
    Applies damage and morale penalties for friendly fire.
    """

    _friendly_fire_events: list[dict] = field(init=False)

    def __post_init__(self):
        self._friendly_fire_events = []

    def check_friendly_fire(
        self,
        attacker_pos: tuple[float, float],
        target_pos: tuple[float, float],
        friendly_units: list,
    ) -> list:
        """
        Check if attack line intersects friendly units.

        Returns:
            List of hit friendly units
        """
        hit_friendlies = []

        for unit in friendly_units:
            ux = (
                getattr(unit.position_component, "x", 0.0)
                if hasattr(unit, "position_component")
                else 0.0
            )
            uy = (
                getattr(unit.position_component, "y", 0.0)
                if hasattr(unit, "position_component")
                else 0.0
            )

            if self._point_near_line(
                attacker_pos,
                target_pos,
                (ux, uy),
                threshold=0.5,
            ):
                hit_friendlies.append(unit)

        return hit_friendlies

    @staticmethod
    def _point_near_line(
        line_start: tuple[float, float],
        line_end: tuple[float, float],
        point: tuple[float, float],
        threshold: float = 0.5,
    ) -> bool:
        """Check if point is near line segment."""
        x0, y0 = line_start
        x1, y1 = line_end
        px, py = point

        line_len_sq = (x1 - x0) ** 2 + (y1 - y0) ** 2
        if line_len_sq == 0:
            return ((px - x0) ** 2 + (py - y0) ** 2) ** 0.5 <= threshold

        t = max(0, min(1, ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / line_len_sq))

        proj_x = x0 + t * (x1 - x0)
        proj_y = y0 + t * (y1 - y0)

        dist = ((px - proj_x) ** 2 + (py - proj_y) ** 2) ** 0.5
        return dist <= threshold

    def apply_friendly_fire_penalty(
        self,
        attacker,
        victim,
        damage: int,
    ) -> dict:
        """
        Apply penalties for friendly fire.

        Returns:
            Dict with damage applied and morale effects
        """
        event = {
            "attacker": getattr(attacker, "name", "Unknown"),
            "victim": getattr(victim, "name", "Unknown"),
            "damage": damage,
            "attacker_morale_change": -20,
            "victim_morale_change": -20,
        }

        # Apply damage to victim
        health = getattr(victim, "health_component", None)
        if health:
            current = getattr(health, "current_hp", 100)
            try:
                new_hp = max(0, int(current) - damage)
                health.current_hp = new_hp
            except (TypeError, ValueError):
                health.current_hp = (
                    max(0, current - damage) if isinstance(current, (int, float)) else 80
                )

        # Apply morale penalty to both
        for unit in [attacker, victim]:
            morale = getattr(unit, "morale_component", None)
            if morale:
                current = getattr(morale, "current_morale", 100.0)
                try:
                    new_morale = max(0.0, float(current) - 20)
                    morale.current_morale = new_morale
                except (TypeError, ValueError):
                    if isinstance(current, (int, float)):
                        morale.current_morale = max(0, current - 20)

        self._friendly_fire_events.append(event)
        return event


@dataclass
class RicochetSystem:
    """
    Ricochet/bounce mechanics.

    High incidence angle (>60 degrees) may cause ricochet.
    Ricochet deals no damage but causes suppression.
    Tank armor slope increases ricochet chance.
    """

    RICOCHET_ANGLE_THRESHOLD: float = 60.0  # degrees
    BASE_RICOCHET_CHANCE: float = 0.3

    def check_ricochet(
        self,
        incidence_angle: float,
        armor_slope: float = 0.0,
    ) -> tuple[bool, float]:
        """
        Check if shot ricochets.

        Args:
            incidence_angle: Angle of impact (degrees)
            armor_slope: Armor slope angle (degrees)

        Returns:
            (is_ricochet, suppression_amount)
        """
        effective_angle = incidence_angle - armor_slope

        if effective_angle > self.RICOCHET_ANGLE_THRESHOLD:
            ricochet_chance = self.BASE_RICOCHET_CHANCE
            slope_bonus = (effective_angle - self.RICOCHET_ANGLE_THRESHOLD) / 30.0
            ricochet_chance = min(0.9, ricochet_chance + slope_bonus)

            if random.random() < ricochet_chance:
                suppression = 0.3 + (effective_angle - 60) / 40
                return (True, min(0.8, suppression))

        return (False, 0.0)
