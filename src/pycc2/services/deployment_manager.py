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
    from pycc2.domain.interfaces.deployment_ui_protocol import IDeploymentUI
    from pycc2.domain.interfaces.display_config import DisplayConfig
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

    Faction Difficulty Asymmetry (G6)
    ----------------------------------
    In CC2, the attacking side and defending side have different advantages:
      - **Attacker**: More requisition points (2400 base), more units,
        but must capture VLs.
      - **Defender**: Fewer RP (1800 base), but starts in good positions
        (closer to VLs), only needs to hold VLs.

    The ``attacker_faction`` field determines which side gets the attacker
    RP bonus.  It is auto-detected from scenario data (the side whose
    deployment zone is farther from VLs is the attacker) or defaults to
    ``"allied"`` (historically accurate for Market Garden).
    """

    deployment_ui: IDeploymentUI | None = None
    deployment_phase_active: bool = False
    attacker_faction: str = "allied"
    _ai_deployments: list[dict] = field(init=False, default_factory=list)
    _ai_units: list = field(init=False, default_factory=list)
    _pending_orders: dict[str, tuple[int, int]] = field(init=False, default_factory=dict)

    # ------------------------------------------------------------------
    # Class constants — asymmetric RP allocation (G6)
    # ------------------------------------------------------------------
    ATTACKER_BASE_RP: int = 2400
    DEFENDER_BASE_RP: int = 1800
    AI_ATTACKER_BASE_RP: int = 1800
    AI_DEFENDER_BASE_RP: int = 1350

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
        deployment_ui: object | None = None,
    ) -> None:
        """Activate the deployment phase.

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
        deployment_ui : object | None
            Pre-created DeploymentUI instance (injected by caller to avoid
            service→presentation coupling). Required — the service layer
            no longer creates presentation objects directly.
        """
        try:
            from pycc2.domain.systems.game_settings import SUPPLY_EFFECTS
            from pycc2.presentation.ui.deployment_factory import (
                build_force_pool_from_settings,
                generate_ai_deployment,
            )

            if deployment_ui is not None:
                self.deployment_ui = deployment_ui
            else:
                raise ValueError(
                    "deployment_ui must be injected by the caller; "
                    "the service layer no longer creates presentation objects directly."
                )

            # Determine attacker faction from scenario data (G6)
            self.attacker_faction = self._detect_attacker_faction(map_data, faction)

            # Calculate requisition points with faction asymmetry (G6)
            # Attacker gets more RP (must advance and capture VLs)
            # Defender gets less RP (but has positional advantage near VLs)
            is_attacker = (
                faction in ("ally", "allied")
                and self.attacker_faction == "allied"
                or faction == "axis"
                and self.attacker_faction == "axis"
            )
            base_rp = self.ATTACKER_BASE_RP if is_attacker else self.DEFENDER_BASE_RP

            requisition_points = base_rp
            max_infantry = 15  # Increased for better gameplay
            max_support = 10  # Increased for better gameplay
            force_pool = None

            if game_settings is not None:
                # Determine player side settings
                if faction in ("ally", "allied"):
                    side_settings = game_settings.allied_settings
                else:
                    side_settings = game_settings.axis_settings

                supply_effects = SUPPLY_EFFECTS[side_settings.supply_level]
                requisition_points = int(base_rp * supply_effects.requisition_point_modifier)

                # Build force pool based on faction
                force_pool = build_force_pool_from_settings(
                    faction=faction,
                    requisition_points=requisition_points,
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

            # Determine enemy faction
            enemy_faction = "axis" if faction in ("ally", "allied") else "allied"

            # Generate AI deployment for enemy side
            self._ai_deployments = []
            if game_settings is not None:
                if enemy_faction == "allied":
                    enemy_supply = game_settings.allied_settings.supply_level
                else:
                    enemy_supply = game_settings.axis_settings.supply_level
                enemy_supply_effects = SUPPLY_EFFECTS[enemy_supply]

                # AI also gets asymmetric RP (G6)
                is_enemy_attacker = (
                    enemy_faction == self.attacker_faction
                    or (enemy_faction == "allied" and self.attacker_faction == "allied")
                    or (enemy_faction == "axis" and self.attacker_faction == "axis")
                )
                enemy_base_rp = (
                    self.AI_ATTACKER_BASE_RP if is_enemy_attacker else self.AI_DEFENDER_BASE_RP
                )
                enemy_rp = int(enemy_base_rp * enemy_supply_effects.requisition_point_modifier)

                try:
                    self._ai_deployments = generate_ai_deployment(
                        map_data=map_data,
                        faction=enemy_faction,
                        requisition_points=enemy_rp,
                    )
                except (RuntimeError, ValueError, AttributeError) as e:
                    logger.warning("Failed to generate AI deployment: %s", e)
                    self._ai_deployments = []
            else:
                # No game_settings — generate default AI deployment so the enemy
                # actually exists in battle. Without this, the player faces zero
                # enemy units and the game is unplayable.
                try:
                    self._ai_deployments = generate_ai_deployment(
                        map_data=map_data,
                        faction=enemy_faction,
                        requisition_points=self.AI_DEFENDER_BASE_RP,
                    )
                except (RuntimeError, ValueError, AttributeError) as e:
                    logger.warning("Failed to generate default AI deployment: %s", e)
                    self._ai_deployments = []

            # Pre-create AI Unit entities (hidden during deployment, ready for battle)
            # These units exist in memory but are NOT added to state.units until
            # complete() is called, so the player never sees them during deployment.
            self._ai_units = self._pre_create_ai_units(enemy_faction)

            logger.info(
                "Deployment phase started — faction=%s, attacker=%s, RP=%d, AI deployments=%d, AI units pre-created=%d",
                faction,
                self.attacker_faction,
                requisition_points,
                len(self._ai_deployments),
                len(self._ai_units),
            )

        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error("Failed to start deployment: %s", e)
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
        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error("Failed to call begin_battle(): %s", e)
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
            logger.warning("No units deployed — battle cannot start without units")
            self.deployment_phase_active = False
            return None

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

        # Add pre-created AI units to game state (already in position, hidden during deployment)
        if not self._ai_units:
            logger.info("No AI units pre-created")
        else:
            for ai_unit in self._ai_units:
                state.units.append(ai_unit)
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
            len(self._ai_units),
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

        logger.info("Applied %d/%d pending orders to units", applied, len(self._pending_orders))
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
                logger.warning(
                    f"Placement {template_id} has invalid position type ({type(pos)}), skipping"
                )
                return None

            if len(pos) < 2:
                logger.warning(f"Placement {template_id} has incomplete position ({pos}), skipping")
                return None

            # Extract coordinates safely
            try:
                x = int(pos[0])
                y = int(pos[1])
            except (ValueError, TypeError) as e:
                logger.warning(
                    f"Placement {template_id} has invalid coordinates ({pos}): {e}, skipping"
                )
                return None

            unit_type = template_type_map.get(
                template_id, type_map.get(unit_type_str, UnitType.INFANTRY_SQUAD)
            )
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

        except (RuntimeError, ValueError, AttributeError) as e:
            logger.error("Failed to create unit from placement: %s", e)
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
            from pycc2.domain.ai.unit_bt_factory import UnitBTFactory
            from pycc2.domain.entities.unit import UnitType

            for u in units:
                if u.faction == ai_faction:
                    if u.unit_type == UnitType.MACHINE_GUN_SQUAD:
                        bt = UnitBTFactory.create_mg_squad_bt(unit_id=u.id)
                    elif u.unit_type == UnitType.COMMANDER:
                        bt = UnitBTFactory.create_commander_bt(unit_id=u.id)
                    else:
                        bt = UnitBTFactory.create_infantry_bt(unit_id=u.id)
                    ai_service.register_ai_unit(u, bt)
        except ImportError as e:
            logger.warning(f"Could not initialize AI behavior tree: {e}")
            logger.info("Continuing without AI behavior trees (units will use default AI)")

    def _pre_create_ai_units(self, enemy_faction: str) -> list:
        """Pre-create AI Unit entities from generated deployments.

        These units are created during the deployment phase but not added
        to the game state until ``complete()`` is called.  This ensures
        they are already in position when the battle starts, while
        remaining invisible to the player during deployment (they are
        not in ``state.units`` so the renderer never draws them).

        Parameters
        ----------
        enemy_faction : str
            The faction string for the enemy side (``"axis"`` or ``"allied"``).

        Returns
        -------
        list[Unit]
            Pre-created AI Unit entities ready to be added to the game state.
        """
        if not self._ai_deployments:
            return []

        from pycc2.domain.entities.unit import Faction, UnitType

        # Determine AI faction enum (consistent with complete())
        ai_faction = Faction.AXIS

        # Build runtime type maps
        type_map = {k: getattr(UnitType, v) for k, v in self._TYPE_MAP.items()}
        template_type_map = {k: getattr(UnitType, v) for k, v in self._TEMPLATE_TYPE_MAP.items()}

        units: list = []
        for counter, ai_placement in enumerate(self._ai_deployments):
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

        logger.info("Pre-created %d AI units (enemy_faction=%s)", len(units), enemy_faction)
        return units

    # ------------------------------------------------------------------
    # Attacker detection (G6)
    # ------------------------------------------------------------------

    @staticmethod
    def _detect_attacker_faction(map_data: dict, player_faction: str) -> str:
        """Detect which faction is the attacker based on scenario data.

        Strategy:
        0. If the scenario has an explicit ``attacker_faction`` field, use it.
        1. If the scenario has ``forces.allies.deployment_zone`` and
           ``forces.axis.deployment_zone``, the side whose zone center
           is farther from the VL center is the attacker.
        2. If the scenario has ``special_rules`` containing
           ``"defender_advantage"``, the *other* side is the attacker.
        3. Default: ``"allied"`` (historically accurate for Market Garden
           — Allies are always on the offensive).

        Parameters
        ----------
        map_data : dict
            Scenario map data, possibly containing ``forces``,
            ``victory_locations``, and ``attacker_faction``.
        player_faction : str
            The player's faction (unused for detection but available
            for future scenario-specific overrides).

        Returns
        -------
        str
            ``"allied"`` or ``"axis"``.
        """
        # Strategy 0: Explicit attacker_faction in scenario data
        explicit_attacker = map_data.get("attacker_faction")
        if explicit_attacker in ("allied", "axis"):
            return explicit_attacker

        forces = map_data.get("forces", {})
        vls = map_data.get("victory_locations", [])

        # Strategy 1: Compare deployment zone centers to VL center
        if forces and vls:
            ally_zone = forces.get("allies", {}).get("deployment_zone")
            axis_zone = forces.get("axis", {}).get("deployment_zone")

            if ally_zone and axis_zone:
                # Calculate zone centers
                ally_cx = (ally_zone.get("x_min", 0) + ally_zone.get("x_max", 0)) / 2
                axis_cx = (axis_zone.get("x_min", 0) + axis_zone.get("x_max", 0)) / 2

                # Calculate VL center
                vl_xs = [
                    vl["position"][0] for vl in vls if "position" in vl and len(vl["position"]) >= 1
                ]
                if vl_xs:
                    vl_cx = sum(vl_xs) / len(vl_xs)

                    # The side farther from VLs is the attacker
                    ally_dist = abs(ally_cx - vl_cx)
                    axis_dist = abs(axis_cx - vl_cx)

                    if ally_dist > axis_dist:
                        return "allied"
                    elif axis_dist > ally_dist:
                        return "axis"

        # Strategy 2: Check special_rules for defender_advantage
        special_rules = map_data.get("special_rules", [])
        if isinstance(special_rules, list) and "defender_advantage" in special_rules:
            # If defender_advantage is set, the defending side is axis
            # (in Market Garden, Germans typically defend)
            return "allied"

        # Default: Allies are the attacker (Market Garden historical accuracy)
        return "allied"
