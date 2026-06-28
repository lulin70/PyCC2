"""CC2 Four-Layer Campaign System — Engine & re-exports.

This is the main entry point for the campaign system.  It re-exports all
public symbols from the split sub-modules so that existing imports (e.g.
``from pycc2.domain.systems.campaign_four_layer import GrandCampaignDefinition``
in ``game_settings.py``) continue to work without changes.

Sub-modules:
  - ``campaign_types.py`` — Frozen dataclass definitions + runtime state classes
  - ``campaign_data.py``  — Market Garden factory function + default instance
  - This file            — ``FourLayerCampaignManager`` orchestration engine
"""

from __future__ import annotations

import logging

from pycc2.domain.entities.squad import MemberState

# -- Re-export: data layer ------------------------------------------------
from pycc2.domain.systems.campaign_data import (  # noqa: F401
    _HP_RECOVERY_PER_DAY,
    _SUPPLY_LINE_AMMO_RESUPPLY,
    DEFAULT_MARKET_GARDEN_CAMPAIGN,
    create_market_garden_campaign,
)

# -- Re-export: type definitions ------------------------------------------
from pycc2.domain.systems.campaign_types import (  # noqa: F401
    BattleDefinition,
    BattleState,
    GrandCampaignDefinition,
    GrandCampaignState,
    OperationDefinition,
    OperationState,
    SectorCampaignDefinition,
    SectorState,
    UnitCarryoverState,
    VictoryLocationDef,
)

logger = logging.getLogger(__name__)


# ========================================================================
# FourLayerCampaignManager — Campaign orchestration with unit carryover
# ========================================================================


class FourLayerCampaignManager:
    """Manages the four-layer campaign with battle-to-battle unit carryover.

    CC2 mechanics:
      - KIA soldiers are removed from the squad permanently
      - WIA soldiers start the next battle with reduced HP
      - Surviving soldiers keep their experience gains
      - Ammo is NOT fully resupplied (only partially, based on supply lines)
    """

    def __init__(self, campaign_def: GrandCampaignDefinition | None = None) -> None:
        """Initialize the four-layer campaign manager with optional custom definition."""
        self._campaign_def = campaign_def or DEFAULT_MARKET_GARDEN_CAMPAIGN
        self._campaign_state = GrandCampaignState()
        self._saved_unit_states: dict[str, UnitCarryoverState] = {}
        self._persistence = None

    @property
    def campaign_definition(self) -> GrandCampaignDefinition:
        """Return the static campaign definition in use."""
        return self._campaign_def

    @property
    def campaign_state(self) -> GrandCampaignState:
        """Return the runtime campaign state."""
        return self._campaign_state

    @property
    def saved_unit_states(self) -> dict[str, UnitCarryoverState]:
        """Return the dict of unit carryover states persisted between battles."""
        return self._saved_unit_states

    def get_battles_for_day(self, day: int) -> list[BattleDefinition]:
        """Get all battles scheduled for a specific day across all sectors."""
        battles: list[BattleDefinition] = []
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    if battle.day == day:
                        battles.append(battle)
        return battles

    def get_operation_for_battle(self, battle_id: str) -> OperationDefinition | None:
        """Find the operation containing a given battle."""
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    if battle.battle_id == battle_id:
                        return operation
        return None

    def get_sector_for_battle(self, battle_id: str) -> SectorCampaignDefinition | None:
        """Find the sector containing a given battle."""
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    if battle.battle_id == battle_id:
                        return sector
        return None

    def advance_day(self) -> None:
        """Advance the campaign to the next day."""
        self._campaign_state.current_day += 1
        if self._campaign_state.current_day > 9:
            self._campaign_state.current_day = 9
            self._campaign_state.victory_determined = True

    def _get_supply_type(self, faction: str, sector_id: str) -> str:
        """Determine supply line type for a faction in a sector."""
        if faction.lower() in ("german", "axis"):
            return "axis_land"

        sector_state = self._campaign_state.sectors.get(sector_id)
        if sector_id == "eindhoven":
            # XXX Corps advances through Eindhoven — land supply
            return "allies_land"
        elif sector_id == "nijmegen":
            # After bridge capture, land supply; before that, airdrop
            if sector_state and sector_state.lz_controlled:
                return "allies_airdrop"
            return "allies_airdrop"
        elif sector_id == "arnhem":
            # Arnhem relies on airdrops; if LZ lost, minimal supply
            if sector_state and not sector_state.lz_controlled:
                return "allies_no_supply"
            return "allies_airdrop"
        return "allies_airdrop"

    # ------------------------------------------------------------------
    # Core carryover methods
    # ------------------------------------------------------------------

    def _save_battle_results(
        self,
        battle_id: str,
        units: list,
    ) -> None:
        """Save each unit's state after a battle ends.

        Captures HP, morale, ammo, experience, KIA/WIA status for carryover
        to the next battle.

        Args:
            battle_id: The battle that just ended
            units: List of Unit objects from the completed battle

        """
        for unit in units:
            unit_id: str = str(getattr(unit, "id", None) or getattr(unit, "unit_id", str(id(unit))))

            # Determine faction
            faction = "allies"
            if hasattr(unit, "faction"):
                f = unit.faction
                faction = f.name.lower() if hasattr(f, "name") else str(f).lower()

            # Determine alive status
            is_alive = True
            if hasattr(unit, "is_alive"):
                is_alive = unit.is_alive
            elif hasattr(unit, "health"):
                is_alive = unit.health.is_alive

            # Get HP
            current_hp = 100.0
            max_hp = 100.0
            if hasattr(unit, "health_component"):
                current_hp = float(unit.health_component.hp)
                max_hp = float(unit.health_component.max_hp)
            elif hasattr(unit, "health"):
                current_hp = float(unit.health.hp)
                max_hp = float(unit.health.max_hp)

            # Get morale
            morale = 100.0
            if hasattr(unit, "morale_component"):
                morale = float(unit.morale_component.value)
            elif hasattr(unit, "morale"):
                morale = float(getattr(unit.morale, "value", 100))

            # Get experience
            experience = 0
            kills = 0
            if hasattr(unit, "veterancy_component") and unit.veterancy_component is not None:
                experience = unit.veterancy_component.xp
                kills = unit.veterancy_component.kills
            elif hasattr(unit, "veterancy") and unit.veterancy is not None:
                experience = unit.veterancy.xp
                kills = unit.veterancy.kills

            # Get ammo
            ammo_remaining = 0
            max_ammo = 0
            if hasattr(unit, "weapon_component") and unit.weapon_component is not None:
                ammo_remaining = unit.weapon_component.ammo_remaining
                max_ammo = unit.weapon_component.max_ammo
            elif hasattr(unit, "weapon") and unit.weapon is not None:
                ammo_remaining = unit.weapon.ammo_remaining
                max_ammo = unit.weapon.max_ammo

            # Determine status
            status = "active"
            if not is_alive:
                status = "kia"
            elif current_hp / max(max_hp, 1) < 0.7:
                status = "wounded"

            # Squad-level carryover
            squad_alive = 0
            squad_wounded = 0
            squad_dead = 0
            squad_total = 0
            if hasattr(unit, "squad_ref") and unit.squad_ref is not None:
                squad = unit.squad_ref
                squad_alive = squad.alive_count
                squad_wounded = squad.wounded_count
                squad_dead = squad.dead_count
                squad_total = squad.size

            carryover = UnitCarryoverState(
                unit_id=unit_id,
                faction=faction,
                is_alive=is_alive,
                current_hp=current_hp,
                max_hp=max_hp,
                morale=morale,
                experience=experience,
                ammo_remaining=ammo_remaining,
                max_ammo=max_ammo,
                kills=kills,
                status=status,
                squad_members_alive=squad_alive,
                squad_members_wounded=squad_wounded,
                squad_members_dead=squad_dead,
                squad_total_size=squad_total,
            )
            self._saved_unit_states[unit_id] = carryover

    def _load_unit_states_for_battle(
        self,
        battle_id: str,
        units: list,
    ) -> list:
        """Apply saved unit states to the new battle's units.

        Carryover rules (CC2 authentic):
          - KIA soldiers are removed from the squad permanently
          - WIA soldiers start the next battle with reduced HP
          - Surviving soldiers keep their experience gains
          - Ammo is NOT fully resupplied (only partially, based on supply lines)

        Args:
            battle_id: The battle about to start
            units: List of Unit objects for the new battle

        Returns:
            Updated units with inherited stats

        """
        if not self._saved_unit_states:
            return units

        # Find the sector for supply line determination
        sector = self.get_sector_for_battle(battle_id)
        sector_id = sector.sector_id if sector else "arnhem"

        inherited_count = 0

        for unit in units:
            unit_id: str = str(getattr(unit, "id", None) or getattr(unit, "unit_id", str(id(unit))))
            saved = self._saved_unit_states.get(unit_id)

            if saved is None:
                continue

            if not saved.is_alive:
                # KIA: Remove from squad permanently
                if hasattr(unit, "health_component"):
                    unit.health_component.hp = 0
                    unit.health_component._update_state()
                elif hasattr(unit, "health"):
                    unit.health.hp = 0
                    unit.health._update_state()

                if hasattr(unit, "state_machine"):
                    from pycc2.domain.entities.unit import UnitState

                    try:
                        unit.state_machine.force_transition(UnitState.DEAD)
                    except (ValueError, RuntimeError) as e:
                        logging.warning("Unit state transition to DEAD failed: %s", e)

                # Remove dead members from squad
                if hasattr(unit, "squad_ref") and unit.squad_ref is not None:
                    unit.squad_ref.remove_dead()

                inherited_count += 1
                continue

            # --- Alive unit: Apply carryover ---

            # HP: WIA soldiers start with reduced HP
            if saved.status == "wounded":
                # Wounded soldiers recover partially between battles
                recovery = saved.max_hp * _HP_RECOVERY_PER_DAY
                new_hp = min(saved.max_hp, saved.current_hp + recovery)
            else:
                # Healthy soldiers keep their HP
                new_hp = saved.current_hp

            if hasattr(unit, "health_component"):
                unit.health_component.hp = int(new_hp)
                unit.health_component._update_state()
            elif hasattr(unit, "health"):
                unit.health.hp = int(new_hp)
                unit.health._update_state()

            # Morale: Partial recovery between battles
            morale_recovery = min(20, 10 + self._campaign_state.current_day * 2)
            new_morale = min(100, int(saved.morale + morale_recovery))
            if hasattr(unit, "morale_component"):
                unit.morale_component.value = new_morale
                unit.morale_component._update_state()
            elif hasattr(unit, "morale"):
                unit.morale.value = new_morale
                unit.morale._update_state()

            # Experience: Surviving soldiers keep their experience gains
            if saved.experience > 0:
                if hasattr(unit, "veterancy_component") and unit.veterancy_component is not None:
                    unit.veterancy_component.add_xp(saved.experience)
                elif hasattr(unit, "veterancy") and unit.veterancy is not None:
                    unit.veterancy.add_xp(saved.experience)

            if saved.kills > 0:
                if hasattr(unit, "veterancy_component") and unit.veterancy_component is not None:
                    unit.veterancy_component.kills += saved.kills
                elif hasattr(unit, "veterancy") and unit.veterancy is not None:
                    unit.veterancy.kills += saved.kills

            # Ammo: NOT fully resupplied — partial resupply based on supply lines
            faction = saved.faction
            supply_type = self._get_supply_type(faction, sector_id)
            resupply_rate = _SUPPLY_LINE_AMMO_RESUPPLY.get(supply_type, 0.3)
            ammo_resupply = int(saved.max_ammo * resupply_rate)
            new_ammo = min(saved.max_ammo, saved.ammo_remaining + ammo_resupply)

            if hasattr(unit, "weapon_component") and unit.weapon_component is not None:
                unit.weapon_component.ammo_remaining = new_ammo
                unit.weapon_component._update_state()
            elif hasattr(unit, "weapon") and unit.weapon is not None:
                unit.weapon.ammo_remaining = new_ammo
                unit.weapon._update_state()

            # Squad-level carryover: Remove KIA members, keep WIA
            if hasattr(unit, "squad_ref") and unit.squad_ref is not None:
                squad = unit.squad_ref
                # Remove dead members from previous battle
                squad.remove_dead()
                # Wounded members keep their wounded state
                for member in squad.members:
                    if member.state == MemberState.WOUNDED:
                        # Wounded soldiers recover partially
                        member.hp = min(100, member.hp + 20)

            inherited_count += 1

        return units

    def get_campaign_summary(self) -> dict:
        """Generate a summary of the campaign outcome.

        Returns a dict with:
          - result: 'ALLIES_VICTORY' / 'AXIS_VICTORY' / 'DRAW'
          - day_ended: the day the campaign ended (1-9)
          - allied_casualties: dict with 'kia' and 'wia' counts
          - axis_casualties: dict with 'kia' and 'wia' counts
          - bridge_status: dict mapping bridge VL names to
            'captured_allied' / 'captured_axis' / 'destroyed' / 'contested'
        """
        state = self._campaign_state

        # --- Determine overall result ---
        # Count victory points across all sectors
        allied_vp = 0
        axis_vp = 0
        for sector_state in state.sectors.values():
            for op_state in sector_state.operations:
                for faction_name, pts in op_state.total_victory_points.items():
                    fname = faction_name.lower()
                    if fname in ("allies", "british", "american", "polish"):
                        allied_vp += pts
                    elif fname in ("axis", "german"):
                        axis_vp += pts

        # Also factor in XXX Corps position for advance_speed sectors
        xxx_pos = state.xxx_corps_position
        if xxx_pos in ("arnhem", "oosterbeek"):
            allied_vp += 100
        elif xxx_pos in ("nijmegen",):
            allied_vp += 50
        elif xxx_pos in ("eindhoven",):
            allied_vp += 25

        if allied_vp > axis_vp * 1.5:
            result = "ALLIES_VICTORY"
        elif axis_vp > allied_vp * 1.5:
            result = "AXIS_VICTORY"
        else:
            result = "DRAW"

        # --- Count casualties from saved unit states ---
        allied_kia = 0
        allied_wia = 0
        axis_kia = 0
        axis_wia = 0
        for unit_state in self._saved_unit_states.values():
            faction = unit_state.faction.lower()
            if faction in ("allies", "british", "american", "polish"):
                if unit_state.status == "kia":
                    allied_kia += 1
                elif unit_state.status == "wounded":
                    allied_wia += 1
            elif faction in ("axis", "german"):
                if unit_state.status == "kia":
                    axis_kia += 1
                elif unit_state.status == "wounded":
                    axis_wia += 1

        # --- Bridge status ---
        bridge_status: dict[str, str] = {}
        for sector in self._campaign_def.sectors:
            for operation in sector.operations:
                for battle in operation.battles:
                    for vl in battle.victory_locations:
                        if vl.vl_type == "bridge":
                            # Check VL control from battle state
                            bridge_sector_state: SectorState | None = state.sectors.get(
                                sector.sector_id
                            )
                            controlled_by = None
                            if bridge_sector_state:
                                for op_state in bridge_sector_state.operations:
                                    for bs in op_state.battle_results:
                                        ctrl = bs.vl_control.get(vl.vl_id)
                                        if ctrl is not None:
                                            fname = ctrl.name.lower()
                                            if fname in ("allies", "british", "american", "polish"):
                                                controlled_by = "captured_allied"
                                            elif fname in ("axis", "german"):
                                                controlled_by = "captured_axis"
                                            else:
                                                controlled_by = "contested"

                            if controlled_by is None:
                                controlled_by = "contested"
                            bridge_status[vl.name] = controlled_by

        return {
            "result": result,
            "day_ended": state.current_day,
            "allied_casualties": {"kia": allied_kia, "wia": allied_wia},
            "axis_casualties": {"kia": axis_kia, "wia": axis_wia},
            "bridge_status": bridge_status,
        }
