"""Deployment Manager — orchestrates the deployment phase of a battle.

Extracted from GameLoop to isolate deployment concerns: creating the
DeploymentUI, generating AI deployments, converting placements into Unit
entities, and initialising the AI service with behaviour trees.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.display_config import DisplayConfig
    from pycc2.presentation.ui.deployment_ui import DeploymentUI
    from pycc2.services.ai_service import AIService

    from .game_loop import GameState

logger = logging.getLogger(__name__)


@dataclass
class DeploymentManager:
    """Manages the deployment phase lifecycle.

    Public API
    ----------
    start(map_data, faction, game_settings, display_config)
        Activate the deployment phase.
    complete(ai_service, state) -> dict | None
        Finalise deployment, create units, and initialise AI.
    get_state() -> object | None
        Return the current DeploymentUI state.
    is_active (property)
        Whether the deployment phase is currently active.
    """

    deployment_ui: DeploymentUI | None = None
    deployment_phase_active: bool = False
    _ai_deployments: list[dict] = field(init=False, default_factory=list)
    _pending_orders: dict[str, tuple[int, int]] = field(init=False, default_factory=dict)

    # ------------------------------------------------------------------
    # Class constants — mapping tables used during unit creation
    # ------------------------------------------------------------------
    _TYPE_MAP: ClassVar[dict[str, str]] = {  # resolved at runtime to UnitType enums
        "infantry": "INFANTRY_SQUAD",
        "support": "MACHINE_GUN_SQUAD",
        "vehicle": "TANK",
        "recon": "SNIPER_TEAM",
    }

    _TEMPLATE_TYPE_MAP: ClassVar[dict[str, str]] = {
        "us_at_team": "AT_GUN_TEAM",
        "ger_at_team": "AT_GUN_TEAM",
        "us_mortar_light": "MORTAR_TEAM",
        "us_mortar_heavy": "MORTAR_TEAM",
        "ger_mortar_light": "MORTAR_TEAM",
        "ger_mortar_heavy": "MORTAR_TEAM",
        "us_officer": "COMMANDER",
        "ger_officer": "COMMANDER",
    }

    _WEAPON_MAP: ClassVar[dict[str, tuple[str, int]]] = {
        "infantry": ("rifle", 120),
        "support": ("mg", 250),
        "vehicle": ("tank_cannon", 30),
        "recon": ("sniper_rifle", 15),
    }

    _TEMPLATE_WEAPON_MAP: ClassVar[dict[str, tuple[str, int]]] = {
        "us_at_team": ("at_gun", 8),
        "ger_at_team": ("at_gun", 8),
        "us_mortar_light": ("mortar", 6),
        "us_mortar_heavy": ("mortar", 6),
        "ger_mortar_light": ("mortar", 6),
        "ger_mortar_heavy": ("mortar", 6),
        "us_officer": ("pistol", 14),
        "ger_officer": ("pistol", 14),
    }

    _HP_MAP: ClassVar[dict[str, int]] = {
        "infantry": 100,
        "support": 80,
        "vehicle": 200,
        "recon": 60,
    }

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_active(self) -> bool:
        return self.deployment_phase_active

    # ------------------------------------------------------------------
    # Public methods
    # ------------------------------------------------------------------

    def start(
        self,
        map_data: dict,
        faction: str = "ally",
        game_settings: object | None = None,
        display_config: DisplayConfig | None = None,
    ) -> None:
        """Create a DeploymentUI and activate the deployment phase.

        Parameters
        ----------
        map_data : dict
            Map data dict with width, height, tiles, spawn_points, etc.
        faction : str
            Player faction ("ally" or "axis").
        game_settings : GameSettings | None
            If provided, used to calculate requisition points and force pool.
        display_config : DisplayConfig | None
            Display configuration for window dimensions.
        """
        try:
            from pycc2.domain.systems.game_settings import SUPPLY_EFFECTS
            from pycc2.presentation.ui.deployment_ui import DeploymentUI as DUI

            width = display_config.window_width if display_config else 800
            height = display_config.window_height if display_config else 600

            self.deployment_ui = DUI(width=width, height=height)

            # Calculate requisition points from game settings
            requisition_points = 2000
            max_infantry = 15   # Increased for better gameplay
            max_support = 10    # Increased for better gameplay
            force_pool = None

            if game_settings is not None:
                # Determine player side settings
                if faction in ("ally", "allied"):
                    side_settings = game_settings.allied_settings
                else:
                    side_settings = game_settings.axis_settings

                supply_effects = SUPPLY_EFFECTS[side_settings.supply_level]
                requisition_points = int(2000 * supply_effects.requisition_point_modifier)

                # Build force pool based on faction
                force_pool = DUI.build_force_pool_from_settings(
                    faction=faction, requisition_points=requisition_points,
                )

            self.deployment_ui.start_deployment_with_settings(
                map_data=map_data,
                faction=faction,
                requisition_points=requisition_points,
                max_infantry=max_infantry,
                max_support=max_support,
                force_pool=force_pool,
            )
            self.deployment_phase_active = True

            # Generate AI deployment for enemy side
            self._ai_deployments = []
            if game_settings is not None:
                enemy_faction = "axis" if faction in ("ally", "allied") else "allied"
                if enemy_faction == "allied":
                    enemy_supply = game_settings.allied_settings.supply_level
                else:
                    enemy_supply = game_settings.axis_settings.supply_level
                enemy_supply_effects = SUPPLY_EFFECTS[enemy_supply]
                enemy_rp = int(1500 * enemy_supply_effects.requisition_point_modifier)

                try:
                    self._ai_deployments = DUI.generate_ai_deployment(
                        map_data=map_data,
                        faction=enemy_faction,
                        requisition_points=enemy_rp,
                    )
                except Exception as e:
                    logger.warning(f"Failed to generate AI deployment: {e}")
                    self._ai_deployments = []

            logger.info(
                "Deployment phase started — faction=%s, RP=%d, AI units=%d",
                faction, requisition_points, len(self._ai_deployments),
            )

        except Exception as e:
            logger.error(f"Failed to start deployment: {e}")
            import traceback
            traceback.print_exc()
            self.deployment_phase_active = False
            raise  # Re-raise to let caller handle it

    def complete(self, ai_service: AIService | None, state: GameState) -> dict | None:
        """Finalize deployment and deactivate the deployment phase.

        Creates Unit entities from player placements and AI deployments,
        adds them to the game state, and initializes the AI service.

        Returns the deployment result dict from DeploymentUI.begin_battle(),
        or None if deployment is not active.
        """
        if not self.deployment_phase_active or self.deployment_ui is None:
            return None

        try:
            result = self.deployment_ui.begin_battle()
        except Exception as e:
            logger.error(f"Failed to call begin_battle(): {e}")
            self.deployment_phase_active = False
            return None

        # Validate result
        if result is None:
            logger.warning("begin_battle() returned None")
            self.deployment_phase_active = False
            return None

        self.deployment_phase_active = False

        # Resolve enums once
        from pycc2.domain.entities.unit import Faction, UnitType

        player_faction = Faction.ALLIES
        ai_faction = Faction.AXIS

        # Build runtime type map (string -> UnitType enum)
        type_map = {k: getattr(UnitType, v) for k, v in self._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in self._TEMPLATE_TYPE_MAP.items()}

        unit_counter = 0

        # Create player units from deployment placements
        placements = result.get("placements", [])
        if not placements:
            logger.warning("No placements in deployment result")

        for placement in placements:
            unit = self._create_unit_from_placement(
                placement=placement,
                faction=player_faction,
                id_prefix="player",
                counter=unit_counter,
                type_map=type_map,
                template_type_map=template_type_map,
            )
            if unit is not None:
                state.units.append(unit)
                unit_counter += 1

        # Create AI units from generated deployments
        if not self._ai_deployments:
            logger.info("No AI deployments generated")
        else:
            for ai_placement in self._ai_deployments:
                unit = self._create_unit_from_placement(
                    placement=ai_placement,
                    faction=ai_faction,
                    id_prefix="ai",
                    counter=unit_counter,
                    type_map=type_map,
                    template_type_map=template_type_map,
                )
                if unit is not None:
                    state.units.append(unit)
                    unit_counter += 1

        # Initialize AI service with deployed AI units
        self._initialize_ai_service(ai_service, state.units, ai_faction)

        # Sync pending orders from DeploymentUI and apply them (GAP-8)
        ui_orders = result.get("pending_orders", {})
        if ui_orders:
            self._pending_orders.update(ui_orders)
        self.apply_pending_orders(state.units)

        logger.info(
            "Deployment complete — player units=%d, AI units=%d, total=%d",
            result.get("infantry_count", 0) + result.get("support_count", 0),
            len(self._ai_deployments),
            len(state.units),
        )

        return result

    def get_state(self) -> object | None:
        """Return the current deployment state, or None if not in deployment."""
        if self.deployment_ui is None:
            return None
        return self.deployment_ui.state

    # ------------------------------------------------------------------
    # Pre-battle orders (GAP-8)
    # ------------------------------------------------------------------

    def set_pending_order(self, unit_id: str, target_x: int, target_y: int) -> None:
        """Set a pending movement order for a unit during deployment.

        The unit will move toward (target_x, target_y) when the battle begins.

        Parameters
        ----------
        unit_id : str
            The ``unit_template_id`` of the placed deployment unit.
        target_x, target_y : int
            Tile coordinates of the movement target.
        """
        self._pending_orders[unit_id] = (target_x, target_y)

    def get_pending_order(self, unit_id: str) -> tuple[int, int] | None:
        """Return the pending order target for a unit, or None."""
        return self._pending_orders.get(unit_id)

    def clear_pending_order(self, unit_id: str) -> None:
        """Remove a pending order for a unit."""
        self._pending_orders.pop(unit_id, None)

    def apply_pending_orders(self, units: list[Unit]) -> None:
        """Apply all pending orders to the given unit list.

        Called after ``complete()`` has created Unit entities.  Finds each
        unit whose template_id matches a pending order and sets its move
        target so it begins moving when the battle starts.

        Matching strategy: use the unit's tile position to find the
        corresponding DeploymentUnit, then look up its template_id in
        the pending orders dict.
        """
        if not self._pending_orders:
            return

        from pycc2.domain.value_objects.tile_coord import TileCoord

        applied = 0
        for unit in units:
            # Match by position: find the deployment unit at this position
            unit_tile = unit.position.tile_coord
            for pu in self.deployment_ui.state.placed_units if self.deployment_ui else []:
                if pu.position == (unit_tile.x, unit_tile.y):
                    order = self._pending_orders.get(pu.unit_template_id)
                    if order:
                        tx, ty = order
                        unit.set_move_target(TileCoord(tx, ty))
                        applied += 1
                    break

        logger.info(
            "Applied %d/%d pending orders to units", applied, len(self._pending_orders)
        )
        self._pending_orders.clear()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _create_unit_from_placement(
        self,
        placement: dict,
        faction: object,
        id_prefix: str,
        counter: int,
        type_map: dict[str, object],
        template_type_map: dict[str, object],
    ) -> Unit | None:
        """Create a single Unit entity from a placement dict.

        Returns None (and logs a warning) if the placement is invalid.
        """
        from pycc2.domain.components.health_component import HealthComponent
        from pycc2.domain.components.morale_component import MoraleComponent
        from pycc2.domain.components.position_component import PositionComponent
        from pycc2.domain.components.vision_component import VisionComponent
        from pycc2.domain.components.weapon_component import WeaponComponent
        from pycc2.domain.entities.unit import Unit, UnitType
        from pycc2.domain.value_objects.tile_coord import TileCoord

        try:
            template_id = placement.get("unit_template_id", "unknown")
            display_name = placement.get("display_name", template_id)
            unit_type_str = placement.get("unit_type", "infantry")
            pos = placement.get("position")

            # Validate position — must be a tuple/list with at least 2 elements
            if pos is None:
                logger.warning(f"Placement {template_id} has no position, skipping")
                return None

            if not isinstance(pos, (tuple, list)):
                logger.warning(f"Placement {template_id} has invalid position type ({type(pos)}), skipping")
                return None

            if len(pos) < 2:
                logger.warning(f"Placement {template_id} has incomplete position ({pos}), skipping")
                return None

            # Extract coordinates safely
            try:
                x = int(pos[0])
                y = int(pos[1])
            except (ValueError, TypeError) as e:
                logger.warning(f"Placement {template_id} has invalid coordinates ({pos}): {e}, skipping")
                return None

            unit_type = template_type_map.get(template_id, type_map.get(unit_type_str, UnitType.INFANTRY_SQUAD))
            weapon_id, max_ammo = self._TEMPLATE_WEAPON_MAP.get(
                template_id, self._WEAPON_MAP.get(unit_type_str, ("rifle", 120))
            )
            max_hp = self._HP_MAP.get(unit_type_str, 100)

            unit = Unit(
                id=f"{id_prefix}_{counter}",
                name=display_name,
                faction=faction,
                unit_type=unit_type,
                position=PositionComponent(tile_coord=TileCoord(x, y)),
                vision=VisionComponent(),
                health=HealthComponent(hp=max_hp, max_hp=max_hp),
                weapon=WeaponComponent(
                    primary_weapon_id=weapon_id,
                    max_ammo=max_ammo,
                    ammo_remaining=max_ammo,
                ),
                morale=MoraleComponent(value=75),
            )
            return unit

        except Exception as e:
            logger.error(f"Failed to create unit from placement: {e}")
            return None

    def _create_ai_units(
        self,
        ai_faction: object,
        unit_counter_start: int,
        type_map: dict[str, object],
        template_type_map: dict[str, object],
    ) -> tuple[list[Unit], int]:
        """Create all AI units from generated deployments.

        Returns (list_of_units, next_counter_value).
        """
        units: list[Unit] = []
        counter = unit_counter_start

        if not self._ai_deployments:
            logger.info("No AI deployments generated")
            return units, counter

        for ai_placement in self._ai_deployments:
            unit = self._create_unit_from_placement(
                placement=ai_placement,
                faction=ai_faction,
                id_prefix="ai",
                counter=counter,
                type_map=type_map,
                template_type_map=template_type_map,
            )
            if unit is not None:
                units.append(unit)
                counter += 1

        return units, counter

    def _initialize_ai_service(
        self,
        ai_service: AIService | None,
        units: list[Unit],
        ai_faction: object,
    ) -> None:
        """Register AI units with the AI service and attach behaviour trees."""
        if ai_service is None:
            return

        try:
            from pycc2.domain.ai.behavior_tree import Selector, Sequence
            from pycc2.domain.ai.tactical_ai import FlankingAI, SuppressionAI

            for u in units:
                if u.faction == ai_faction:
                    # Create a simple behavior tree for each AI unit
                    bt = Selector([
                        Sequence([FlankingAI()]),
                        Sequence([SuppressionAI()]),
                    ])
                    ai_service.register_ai_unit(u, bt)
        except ImportError as e:
            logger.warning(f"Could not initialize AI behavior tree: {e}")
            logger.info("Continuing without AI behavior trees (units will use default AI)")
