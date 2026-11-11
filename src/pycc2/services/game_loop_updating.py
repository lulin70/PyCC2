"""Game Loop Updating Mixin — extracted from game_loop.py (P5-1 batch 2).

Contains the per-tick update methods used by the GameLoop facade:
  - _update_logic: top-level update dispatcher (called each logic tick)
  - _update_weather: weather system + day-night cycle
  - _update_audio_sync: environmental audio context sync
  - _update_unit_movement: unit movement + arrival detection
  - _update_fatigue: fatigue accumulation/recovery + attack line tracking
  - _update_combat: combat director tick + queued command processing
  - _update_popups: trigger combat popup scan (delegates to combat mixin)
  - _update_camera: camera screen shake update
  - _update_visual_effects: flash/weather/shell/trails/shadows
  - _update_hud: HUD fade transitions
  - _ensure_ai_units_registered: safety net for unregistered enemy units
  - _update_ai: AI service tick
  - _update_victory: victory manager evaluation

This is a mixin — do not instantiate directly. The facade GameLoop class
inherits this mixin and provides all required attributes via its dataclass
fields. Class-level attribute declarations below tell mypy which facade
fields the mixin methods rely on. _update_popups delegates to
self._process_combat_popups() which is provided by GameLoopCombatMixin.
"""

from __future__ import annotations

import contextlib
import logging
from typing import TYPE_CHECKING

from pycc2.domain.entities.unit import UnitState
from pycc2.domain.interfaces import (
    ICombatDirector,
    IDayNightCycle,
    IDynamicShadowSystem,
    IEffectStack,
    IEnvironmentalAudio,
    IHUDManager,
    IProjectileTrailSystem,
    IVictoryManager,
    IWeatherState,
    IWeatherSystem,
)
from pycc2.services.game_loop_types import LOGIC_DT, GameState

if TYPE_CHECKING:
    from pycc2.domain.interfaces.interaction_controller_protocol import (
        IInteractionController as InteractionController,
    )
    from pycc2.domain.interfaces.renderer_protocol import IRenderer as EnhancedRenderer
    from pycc2.infrastructure.events.event_bus import EventBus
    from pycc2.presentation.audio.sound_system import SoundSystem
    from pycc2.services.ai_service import AIService

logger = logging.getLogger(__name__)

_ARMOR_TYPE_KEYS = ("TANK", "VEHICLE", "HALFTRACK", "ARMORED")


def _is_armor_unit(unit: object) -> bool:
    """Return True for tank/vehicle units (PF-12 combined arms)."""
    unit_type = getattr(unit, "unit_type", None)
    name = getattr(unit_type, "name", "").upper()
    if "ANTI_TANK" in name:
        return False
    return any(key in name for key in _ARMOR_TYPE_KEYS)


class GameLoopUpdatingMixin:
    """Per-tick update methods for GameLoop. Inherited by the facade."""

    # -- Facade attributes used by update methods (no defaults; set by GameLoop) --
    state: GameState
    renderer: EnhancedRenderer
    event_bus: EventBus
    sound_system: SoundSystem | None
    ai_service: AIService | None
    interaction_controller: InteractionController | None
    _combat_director: ICombatDirector | None
    _victory_manager: IVictoryManager | None
    _weather_system: IWeatherSystem | None
    _weather_effects: object | None
    _weather_state: IWeatherState | None
    _day_night_cycle: IDayNightCycle | None
    _environmental_audio: IEnvironmentalAudio | None
    _day_night_time: float | None
    _effect_stack: IEffectStack | None
    _projectile_trail_sys: IProjectileTrailSystem | None
    _dynamic_shadow_sys: IDynamicShadowSystem | None
    _hud_manager: IHUDManager | None
    _fog_of_war_service: object | None
    _reinforcement_service: object | None
    _logistics_counter: int
    _ai_tick_counter: int
    _ai_update_interval: int

    # -- Cross-mixin method provided by GameLoopCombatMixin --
    def _process_combat_popups(self) -> None:
        """Scan combat events and spawn floating popups. Provided by GameLoopCombatMixin."""
        ...

    def _update_logic(self, dt: float) -> None:
        if self.state.paused:
            return
        if self._combat_director is None:
            return

        self._update_weather(dt)
        self._update_fog_of_war()
        self._update_reinforcements()
        self._update_logistics()
        self._update_audio_sync(dt)
        self._update_unit_movement(dt)
        self._update_fatigue(dt)
        self._update_scenario_effects()
        self._update_combat(dt)
        self._update_popups()
        self._update_camera(dt)
        self._update_visual_effects(dt)
        self._update_hud(dt)
        self._update_ai(dt)
        self._update_victory()

    def _update_weather(self, dt: float) -> None:
        # Update weather system
        if self._weather_system is not None:
            self._weather_system.update(dt)

        # Apply weather effects to game state
        if self._weather_effects is not None and self._weather_state is not None:
            weather_type = self._weather_state.weather_type
            changed = self.state.current_weather != weather_type
            self.state.current_weather = weather_type
            if self.state.game_map is not None:
                self.state.game_map.weather_state = self._weather_state
            if changed and getattr(self, "_los_system", None) is not None:
                self._los_system.set_weather(weather_type)

        # Update day-night cycle
        if self._day_night_cycle is not None:
            self._day_night_cycle.advance(dt)

    def _matching_vl_ids(self, *needles: str) -> list[str]:
        """Return ids of objectives whose id/name contains any needle (PF-12)."""
        if self.state.game_map is None:
            return []
        ids: list[str] = []
        for obj in self.state.game_map.objectives:
            text = f"{getattr(obj, 'id', '')} {getattr(obj, 'name', '')}".lower()
            if any(needle in text for needle in needles):
                ids.append(str(getattr(obj, "id", "")))
        return ids

    def _vl_owner_map(self) -> dict[str, str | None]:
        """Return current VL ownership from the victory manager (PF-12)."""
        manager = getattr(self, "_victory_manager", None)
        if manager is None or not hasattr(manager, "get_vl_owners"):
            return {}
        return manager.get_vl_owners()

    def _update_reinforcements(self) -> None:
        """Spawn scenario reinforcements when their arrival turn is reached."""
        service = self._reinforcement_service
        manager = getattr(self, "_deployment_manager", None)
        if service is None or manager is None:
            return
        if self.state.game_map is None:
            return

        rules = getattr(self, "_scenario_rules", None)
        allowed_sides: set[str] | None = None
        max_per_side: int | None = None
        if rules is not None:
            if rules.has("lz_must_hold_for_reinforcements"):
                lz_ids = self._matching_vl_ids("lz", "landing")
                owners = self._vl_owner_map()
                if lz_ids and not any(owners.get(vl) == "allies" for vl in lz_ids):
                    allowed_sides = {"axis"}
            if rules.has("limited_reinforcements"):
                max_per_side = 2

        try:
            spawned = service.update(
                tick=self.state.tick,
                units=self.state.units,
                game_map=self.state.game_map,
                factory=manager.create_reinforcement_unit,
                allowed_sides=allowed_sides,
                max_per_side=max_per_side,
            )
        except Exception:
            logger.warning("Reinforcement update failed", exc_info=True)
            return
        for unit, side in spawned:
            logger.info("Reinforcement joined battle: %s (%s)", unit.id, side)

    def _update_logistics(self) -> None:
        """Resupply nearby friendly units from their rear spawn area every ~2 s."""
        self._logistics_counter += 1
        if self._logistics_counter < 60:
            return
        self._logistics_counter = 0

        spawn_points = self._scenario_data.get("spawn_points", []) if self._scenario_data else []
        if not spawn_points:
            return

        rules = getattr(self, "_scenario_rules", None)
        air_level = getattr(self.state, "air_support_level", "full")
        if rules is not None and rules.has("corridor_must_remain_open"):
            corridor_ids = self._matching_vl_ids(
                "corridor", "road", "junction", "highway", "crossroads"
            )
            owners = self._vl_owner_map()
            if corridor_ids and any(owners.get(vl) == "axis" for vl in corridor_ids):
                logger.debug("Supply blocked: corridor VL lost")
                return

        for unit in self.state.units:
            if not getattr(unit, "is_alive", False):
                continue
            weapon = getattr(unit, "weapon", None)
            reserve = getattr(weapon, "reserve_ammo", -2)
            if weapon is None or reserve < 0:
                continue

            faction_name = getattr(getattr(unit, "faction", None), "name", "")
            unit_side = (
                "allies" if faction_name in ("ALLIES", "AMERICAN", "BRITISH", "POLISH") else "axis"
            )
            pos = unit.position.tile_coord
            near = any(
                sp.get("side") == unit_side
                and abs(int(sp.get("position", [0, 0])[0]) - pos.x)
                + abs(int(sp.get("position", [0, 0])[1]) - pos.y)
                <= 3
                for sp in spawn_points
                if isinstance(sp, dict)
            )
            if not near:
                continue

            amount = max(1, weapon.max_ammo // 10)
            if rules is not None and rules.has("supply_dwindling"):
                amount = int(amount * getattr(self, "_supply_decay", 1.0))
            if unit_side == "allies":
                if air_level == "none":
                    continue
                if air_level == "limited":
                    amount //= 2
            if amount <= 0:
                continue

            cap = weapon.max_ammo * 2
            if weapon.reserve_ammo < cap:
                weapon.reserve_ammo = min(cap, weapon.reserve_ammo + amount)

        if rules is not None and rules.has("supply_dwindling"):
            self._supply_decay = max(0.0, getattr(self, "_supply_decay", 1.0) * 0.85)

    def _update_scenario_effects(self) -> None:
        """Apply PF-12 rules that act every tick or every second."""
        rules = getattr(self, "_scenario_rules", None)
        if rules is None or not rules.rules:
            return
        units = self.state.units

        if rules.has("fanatic_defenders"):
            for unit in units:
                if unit.is_alive and unit.faction.name == "AXIS" and unit.morale.value < 30:
                    unit.morale.value = 30

        if not rules.has("combined_arms_bonus"):
            return
        self._combined_arms_counter = getattr(self, "_combined_arms_counter", 0) + 1
        if self._combined_arms_counter % 30 != 0:
            return

        armor = [unit for unit in units if unit.is_alive and _is_armor_unit(unit)]
        if not armor:
            return
        for unit in units:
            if not unit.is_alive:
                continue
            pos = unit.position.tile_coord
            supported = any(
                other.faction == unit.faction
                and max(
                    abs(other.position.tile_coord.x - pos.x),
                    abs(other.position.tile_coord.y - pos.y),
                )
                <= 4
                for other in armor
            )
            unit.scenario_accuracy_mod = 1.10 if supported else 1.0

    def _update_fog_of_war(self) -> None:
        # Recompute per-faction visibility (5-tick interval handled by service).
        # A fog failure must never break the main loop.
        # PF-14: skip during deployment — the player has no units placed yet,
        # so an update would mark the whole map HIDDEN and black out the
        # deployment screen. Fog starts with the first battle tick.
        dm = getattr(self, "_deployment_manager", None)
        if dm is not None and dm.is_active:
            return
        if self._fog_of_war_service is None:
            return
        try:
            self._fog_of_war_service.update(self.state.units, self.state.game_map, self.state.tick)
        except Exception:
            logger.warning("Fog-of-war update failed, keeping last grid", exc_info=True)

    def _update_audio_sync(self, dt: float) -> None:
        # Process audio event queue
        if self.sound_system:
            self.sound_system.process_event_queue()

        # Update environmental ambient audio system
        if self._environmental_audio is not None:
            with contextlib.suppress(Exception):
                self._environmental_audio.update(dt)

        # Sync environmental audio context with game state
        if self._environmental_audio is not None:
            try:
                # Sync time-of-day from day-night cycle
                if self._day_night_cycle is not None:
                    tod = self._day_night_cycle.time_of_day
                    if tod is not None:
                        hour = int(tod) % 24
                        self._environmental_audio.set_time_of_day(hour)
                elif self._day_night_time is not None:
                    hour = int(self._day_night_time * 24) % 24
                    self._environmental_audio.set_time_of_day(hour)

                # Sync weather (rain)
                if self._weather_state is not None:
                    weather_type = self._weather_state.weather_type
                    if weather_type is not None:
                        is_raining = "rain" in str(weather_type).lower()
                        self._environmental_audio.set_weather_rain(is_raining)

                # Estimate combat intensity from unit states (single pass)
                attacking_count = 0
                total_alive = 0
                for u in self.state.units:
                    if u.is_alive:
                        total_alive += 1
                        if u.state_machine.current == UnitState.ATTACKING:
                            attacking_count += 1
                intensity = min(1.0, attacking_count / max(1, total_alive * 0.15))
                self._environmental_audio.set_combat_intensity(intensity)
            except (AttributeError, ValueError, TypeError):
                pass

    def _update_unit_movement(self, dt: float) -> None:
        # Update unit movements (smooth movement toward targets)
        for unit in self.state.units:
            # Update movement mode timers (Fast Move, Sneak, Defend)
            unit.update_movement_mode()

            if unit.move_target is not None:
                arrived = unit.update_movement(dt)
                if arrived:
                    logger.debug("[MOVEMENT] %s arrived at destination", unit.display_name)

    def _update_fatigue(self, dt: float) -> None:
        # Update unit fatigue, veterancy, and weather effects
        for unit in self.state.units:
            # Fatigue accumulation
            if unit.fatigue is not None:
                if unit.move_target is not None:
                    activity = "fast_move" if unit.is_fast_moving else "moving"
                    unit.fatigue.accumulate(activity)
                elif unit.state_machine.current == UnitState.ATTACKING:
                    unit.fatigue.accumulate("firing")
                else:
                    unit.fatigue.recover()

            # Veterancy: record shots (integration point for combat)
            # (actual XP from kills is handled in combat_director)

        # Update attack line tracking (unit targets follow movement)
        if self.interaction_controller:
            self.interaction_controller.attack_line.update_tracking(self.state.units)

    def _update_combat(self, dt: float) -> None:
        if self._combat_director is None:
            return
        battle_stats = self._victory_manager.battle_stats if self._victory_manager else None
        self._combat_director.update(
            units=self.state.units,
            game_map=self.state.game_map,
            dt=dt,
            battle_stats=battle_stats,
        )
        self._combat_director.process_effects(renderer=self.renderer, camera=self.state.camera)

        # Process queued commands for units that completed their current command
        for unit in self.state.units:
            if not unit.is_alive:
                continue
            if unit.state_machine.current == UnitState.IDLE and unit.has_queued_commands:
                next_cmd = unit.get_next_queued_command()
                if next_cmd is not None:
                    unit._execute_queued_command(next_cmd)

    def _update_popups(self) -> None:
        # Trigger combat popups for significant events
        self._process_combat_popups()

    def _update_camera(self, dt: float) -> None:
        # Update camera screen shake
        self.state.camera.update_shake(dt)

    def _update_visual_effects(self, dt: float) -> None:
        # P2-03: Update screen flash overlay alpha (fade-out)
        self.renderer.update_flash(dt)
        self.renderer.update_weather(dt)
        self.renderer.update_shell_casings(dt)
        self.renderer.update_suppression_overlay(dt, self.state.units)
        self.renderer._smooth_positions(self.state.units, dt)

        # Update cinematic camera effect stack
        if self._effect_stack is not None:
            self._effect_stack.update(dt)

        # Update projectile trail system
        if self._projectile_trail_sys is not None:
            self._projectile_trail_sys.update(dt)

        # Update dynamic shadow time-of-day
        if self._dynamic_shadow_sys is not None:
            if self._day_night_time is not None:
                self._dynamic_shadow_sys.set_time_of_day(self._day_night_time)
            elif self._day_night_cycle is not None:
                tod = self._day_night_cycle.time_of_day
                normalized = tod / 24.0
                self._dynamic_shadow_sys.set_time_of_day(normalized)

    def _update_hud(self, dt: float) -> None:
        # P2-05: Update UI fade transitions (HUDManager panel/minimap fades)
        if self._hud_manager is not None:
            self._hud_manager.update(dt)

    def _ensure_ai_units_registered(self) -> None:
        """Safety net: auto-register non-player units that lack AI behavior trees.

        This handles cases where units are added directly to state.units
        without going through the deployment flow (e.g., test scripts,
        debug commands, or scenario editors).
        """
        if self.ai_service is None:
            return

        # Determine player faction from existing registrations or default
        player_faction = getattr(self.state, "player_faction", None)
        if player_faction is None:
            # Heuristic: if any ALLIES unit exists, player is ALLIES
            from pycc2.domain.entities.unit import Faction

            has_allies = any(u.faction == Faction.ALLIES for u in self.state.units)
            player_faction = Faction.ALLIES if has_allies else Faction.AXIS

        # Find unregistered enemy units
        registered_ids = set(self.ai_service._unit_entities.keys())
        unregistered_enemies = [
            u
            for u in self.state.units
            if u.id not in registered_ids and u.faction != player_faction and u.is_alive
        ]

        if not unregistered_enemies:
            return

        try:
            from pycc2.domain.ai.unit_bt_factory import UnitBTFactory
            from pycc2.domain.entities.unit import UnitType

            for unit in unregistered_enemies:
                # Select appropriate behavior tree by unit type
                if unit.unit_type == UnitType.MACHINE_GUN_SQUAD:
                    bt = UnitBTFactory.create_mg_squad_bt(unit_id=unit.id)
                elif unit.unit_type == UnitType.COMMANDER:
                    bt = UnitBTFactory.create_commander_bt(unit_id=unit.id)
                else:
                    bt = UnitBTFactory.create_infantry_bt(unit_id=unit.id)

                self.ai_service.register_ai_unit(unit, bt)
                logger.info(
                    "Auto-registered AI unit: %s [%s] (%s)",
                    unit.name,
                    unit.id,
                    unit.unit_type.name,
                )
        except ImportError as e:
            logger.warning("Could not auto-register AI units: %s", e)

    def _update_ai(self, dt: float) -> None:
        # Safety net: ensure enemy units are registered before ticking
        self._ensure_ai_units_registered()

        if self.ai_service is not None and self.ai_service.managed_unit_count > 0:
            self._ai_tick_counter += 1
            if self._ai_tick_counter >= self._ai_update_interval:
                try:
                    intents = self.ai_service.tick(
                        dt,
                        game_map=self.state.game_map,
                        all_units=self.state.units,
                    )
                    if intents:
                        self.ai_service.execute_intents(intents)
                except Exception:
                    # TD-039: AI tick failure degrades to idle units this tick.
                    # Log warning and continue — do not propagate the exception
                    # (a single AI bug should not crash the whole game).
                    logger.warning(
                        "AI tick failed, units idle this tick",
                        exc_info=True,
                    )
                self._ai_tick_counter = 0

    def _update_victory(self) -> None:
        if self._victory_manager is None:
            return
        victory_outcome = self._victory_manager.evaluate(self.state.units, self.state.tick)
        if victory_outcome is not None:
            result, reason = victory_outcome
            self.state.paused = True

            # Publish BattleWon named event for camera effects and achievement tracking
            self.event_bus.publish_named(
                "BattleWon",
                {
                    "result": result.name,
                    "reason": reason,
                    "duration_seconds": self.state.tick * LOGIC_DT,
                },
            )

            if self.sound_system:
                from pycc2.domain.value_objects.audio_enums import SoundType

                if result.name == "ALLIES_VICTORY":
                    self.sound_system.play(SoundType.UI_COMMAND)
                else:
                    self.sound_system.play(SoundType.UI_CANCEL)


__all__ = ["GameLoopUpdatingMixin"]
