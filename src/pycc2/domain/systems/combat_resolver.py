from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pycc2.domain.systems.morale_system import MoraleEvent
from pycc2.domain.systems.spatial_hash import SpatialHash

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.domain.entities.unit import Unit
    from pycc2.domain.systems.ballistic import BallisticEngine, ShotResult
    from pycc2.domain.systems.morale_system import MoraleCalculator
    from pycc2.services.event_bus import EventBus
    from pycc2.services.random_context import RandomContext


@dataclass(slots=True)
class CombatResolver:
    ballistic_engine: BallisticEngine
    morale_calc: MoraleCalculator
    rng: RandomContext
    event_bus: EventBus | None = None

    def resolve_attack(
        self,
        attacker: Unit,
        target: Unit,
        game_map: GameMap | None = None,
    ) -> dict:
        events_fired: list[str] = []

        if not attacker.can_act or not target.is_alive:
            return {
                "shot_result": None,
                "morale_result": None,
                "events_fired": events_fired,
            }

        shot_result: ShotResult = self.ballistic_engine.calculate_shot(
            attacker, target, weapon_slot="primary", game_map=game_map
        )

        morale_result = self._apply_damage_and_events(attacker, target, shot_result, events_fired)
        self._apply_suppression(target, shot_result, events_fired)
        self._fire_weapon_event(attacker, target, shot_result, events_fired)

        return {
            "shot_result": shot_result,
            "morale_result": morale_result,
            "events_fired": events_fired,
        }

    def _apply_damage_and_events(
        self,
        attacker: Unit,
        target: Unit,
        shot_result: ShotResult,
        events_fired: list[str],
    ) -> None | dict:
        morale_result = None
        if not shot_result.hit:
            return morale_result

        # Building garrison hard cover bonus: reduce incoming damage by 50%
        damage_amount = int(shot_result.damage_dealt)
        if target.current_building_pos is not None:
            # R1: Multi-floor combat modifiers
            # Upper floors: better LOS (already in building) but more vulnerable to artillery
            floor = getattr(target, 'building_floor', 0)
            if floor > 0:
                # Upper floor: less cover from direct fire (windows expose more)
                cover_reduction = 1.0 - floor * 0.15  # 15% less cover per floor
                damage_amount = max(1, int(damage_amount * (1.0 - 0.5 * cover_reduction)))
            else:
                damage_amount = max(1, damage_amount // 2)

        actual_damage = target.take_damage(damage_amount)

        if self.event_bus is not None:
            event: dict = {
                "attacker_id": attacker.id,
                "target_id": target.id,
                "is_hit": True,
                "damage": float(actual_damage),
            }
            self.event_bus.publish(event)
            events_fired.append("UnitAttacked")

        if shot_result.is_killing_blow or not target.is_alive:
            target.die()

            if self.event_bus is not None:
                killed_event: dict = {
                    "unit_id": target.id,
                    "faction": target.faction.name,
                    "position": (
                        target.position.tile_coord.x,
                        target.position.tile_coord.y,
                    ),
                }
                self.event_bus.publish(killed_event)
                events_fired.append("UnitKilled")

            morale_result = self.morale_calc.calculate_event_effect(
                target.morale,
                MoraleEvent.ALLY_KILLED,
            )

        return morale_result

    def _apply_suppression(
        self,
        target: Unit,
        shot_result: ShotResult,
        events_fired: list[str],
    ) -> None:
        suppression_amount = int(shot_result.suppression_dealt)
        if suppression_amount <= 0:
            return

        # Building garrison bonus: reduce suppression accumulation by 40%
        if target.current_building_pos is not None:
            suppression_amount = max(1, int(suppression_amount * 0.6))

        # R3: Veteran units resist suppression better
        if target.veterancy is not None:
            resist = target.veterancy.morale_resistance  # 1.0 recruit, 1.35 elite
            suppression_amount = max(1, int(suppression_amount / resist))

        old_morale = target.morale.value
        target.morale.add_suppression(suppression_amount)

        if self.event_bus is not None:
            morale_event: dict = {
                "unit_id": target.id,
                "old_value": old_morale,
                "new_value": target.morale.value,
                "event_type": f"suppression +{suppression_amount}",
                "state_changed": True,
            }
            self.event_bus.publish(morale_event)
            events_fired.append("MoraleChanged")

    def _fire_weapon_event(
        self,
        attacker: Unit,
        target: Unit,
        shot_result: ShotResult,
        events_fired: list[str],
    ) -> None:
        fired = attacker.weapon.fire()

        if self.event_bus is not None and fired:
            fired_event: dict = {
                "unit_id": attacker.id,
                "weapon_id": attacker.weapon.primary_weapon_id,
                "target_id": target.id,
                "hit": shot_result.hit,
                "ammo_remaining": attacker.weapon.ammo_remaining,
            }
            self.event_bus.publish(fired_event)
            events_fired.append("WeaponFired")

    def resolve_combat_turn(
        self,
        allies_units: list[Unit],
        axis_units: list[Unit],
        game_map: GameMap,
    ) -> list[dict]:
        results: list[dict] = []
        all_units = allies_units + axis_units

        # Build spatial hash for efficient target selection
        spatial = SpatialHash(cell_size=10)
        for u in all_units:
            if u.is_alive:
                spatial.insert(u.id, u.position.tile_coord, u.faction)

        for attacker in all_units:
            if not attacker.can_act:
                continue

            # Query enemies within weapon range using spatial hash
            weapon_range = self._get_weapon_range(attacker)
            enemies_nearby = spatial.query_radius(
                attacker.position.tile_coord, weapon_range,
                exclude_faction=attacker.faction,
            )
            if not enemies_nearby:
                continue

            # Select best target from nearby enemies
            target = self._select_best_target(attacker, enemies_nearby, all_units, game_map)
            if target is None:
                continue

            result = self.resolve_attack(attacker, target, game_map=game_map)
            results.append(result)

        return results

    def _get_weapon_range(self, attacker: Unit) -> int:
        """Return the weapon's max range for the attacker (default 12 if unknown)."""
        weapon_range = getattr(attacker.weapon, "max_range", None)
        if weapon_range is not None:
            return int(weapon_range)
        return 12

    def _select_best_target(
        self,
        attacker: Unit,
        enemy_ids: list[str],
        all_units: list[Unit],
        game_map: GameMap,
    ) -> Unit | None:
        """Select the best target from enemy IDs using threat scoring.

        Scores each enemy by distance, threat, and health, then returns
        the highest-scoring target.
        """
        unit_map = {u.id: u for u in all_units}
        best_target: Unit | None = None
        best_score = float("-inf")

        attacker_pos = attacker.position.tile_coord

        for eid in enemy_ids:
            enemy = unit_map.get(eid)
            if enemy is None or not enemy.is_alive:
                continue

            # Distance factor: closer is better (inverse distance)
            dist = max(attacker_pos.chebyshev_distance(enemy.position.tile_coord), 1)
            distance_score = 1.0 / dist

            # Threat factor: higher HP ratio and unit type weight
            hp_ratio = float(enemy.health.hp_ratio)
            threat_score = hp_ratio

            # Health factor: prefer lower health targets (easier to kill)
            health_score = 1.0 - hp_ratio

            combined = distance_score * 0.4 + threat_score * 0.3 + health_score * 0.3

            if combined > best_score:
                best_score = combined
                best_target = enemy

        return best_target
