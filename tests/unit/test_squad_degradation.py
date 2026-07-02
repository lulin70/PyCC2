"""Tests for SquadDegradationManager and NCORallyBehavior — squad leadership loss effects."""

from __future__ import annotations

from pycc2.domain.ai.squad_degradation import (
    ADVANCED_TACTICS,
    BASIC_TACTICS,
    NCORallyBehavior,
    SquadDegradationManager,
    SquadState,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    uid: str = "u1",
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    morale: int = 80,
    squad_id: str | None = None,
    is_squad_leader: bool = False,
) -> Unit:
    unit = Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=Faction.ALLIES,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=100),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=8, max_ammo=8),
        position=PositionComponent(tile_coord=TileCoord(10, 10)),
        vision=VisionComponent(range_tiles=6),
    )
    unit.squad_id = squad_id
    unit.is_squad_leader = is_squad_leader
    return unit


class TestSquadDegradationManager:
    """Test squad degradation state tracking and modifier calculation."""

    def test_register_and_get_default_state(self):
        """Verify: newly registered squad starts in COMBAT_READY state.

        Scenario: Register a squad with unit IDs.
        Expected: get_squad_state returns COMBAT_READY.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1", "u2", "u3"])
        assert mgr.get_squad_state("squad_1") == SquadState.COMBAT_READY

    def test_get_squad_state_unknown_squad_returns_combat_ready(self):
        """Verify: querying an unregistered squad returns COMBAT_READY default.

        Scenario: Query squad that was never registered.
        Expected: Returns COMBAT_READY (safe default).
        """
        mgr = SquadDegradationManager()
        assert mgr.get_squad_state("nonexistent") == SquadState.COMBAT_READY

    def test_unregister_squad_removes_record(self):
        """Verify: unregistering a squad clears its records and unit mappings.

        Scenario: Register then unregister a squad.
        Expected: Squad state reverts to COMBAT_READY default.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1", "u2"])
        mgr.unregister_squad("squad_1")
        assert mgr.get_squad_state("squad_1") == SquadState.COMBAT_READY

    def test_get_modifiers_combat_ready_has_no_penalties(self):
        """Verify: COMBAT_READY state has zero penalties.

        Scenario: Get modifiers for a fresh squad.
        Expected: All penalty values are zero/False.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1"])
        mods = mgr.get_modifiers("squad_1")
        assert mods.accuracy_penalty == 0.0
        assert mods.reaction_delay_pct == 0.0
        assert mods.morale_penalty == 0
        assert mods.panic_contagion_risk is False

    def test_get_accuracy_modifier_combat_ready_is_1(self):
        """Verify: accuracy multiplier is 1.0 for COMBAT_READY.

        Scenario: Get accuracy modifier for fresh squad.
        Expected: 1.0 (no penalty).
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1"])
        assert mgr.get_accuracy_modifier("squad_1") == 1.0

    def test_get_reaction_delay_multiplier_combat_ready_is_1(self):
        """Verify: reaction delay multiplier is 1.0 for COMBAT_READY.

        Scenario: Get reaction delay for fresh squad.
        Expected: 1.0 (no delay).
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1"])
        assert mgr.get_reaction_delay_multiplier("squad_1") == 1.0

    def test_is_tactic_available_combat_ready_allows_all(self):
        """Verify: COMBAT_READY allows both advanced and basic tactics.

        Scenario: Check tactic availability for fresh squad.
        Expected: All tactics return True.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1"])
        for tactic in ADVANCED_TACTICS | BASIC_TACTICS:
            assert mgr.is_tactic_available("squad_1", tactic) is True

    def test_get_available_tactics_combat_ready_returns_all(self):
        """Verify: COMBAT_READY returns union of advanced and basic tactics.

        Scenario: Get available tactics for fresh squad.
        Expected: All tactics available.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("squad_1", ["u1"])
        tactics = mgr.get_available_tactics("squad_1")
        assert tactics == ADVANCED_TACTICS | BASIC_TACTICS

    def test_on_leader_killed_commander_causes_severe_degradation(self):
        """Verify: platoon commander death triggers SEVERE degradation.

        Scenario: Commander unit killed in a registered squad.
        Expected: Squad state becomes DEGRADED_SEVERE.
        """
        mgr = SquadDegradationManager()
        commander = _make_unit("cmdr", UnitType.COMMANDER, squad_id="squad_1")
        soldier = _make_unit("u1", squad_id="squad_1", morale=80)
        mgr.register_squad("squad_1", ["cmdr", "u1"])
        mgr.on_leader_killed(commander, [commander, soldier])
        assert mgr.get_squad_state("squad_1") == SquadState.DEGRADED_SEVERE

    def test_on_leader_killed_squad_leader_causes_moderate(self):
        """Verify: squad leader death triggers MODERATE degradation.

        Scenario: Squad leader unit killed.
        Expected: Squad state becomes DEGRADED_MODERATE.
        """
        mgr = SquadDegradationManager()
        leader = _make_unit("leader", is_squad_leader=True, squad_id="squad_1")
        soldier = _make_unit("u1", squad_id="squad_1", morale=80)
        mgr.register_squad("squad_1", ["leader", "u1"])
        mgr.on_leader_killed(leader, [leader, soldier])
        assert mgr.get_squad_state("squad_1") == SquadState.DEGRADED_MODERATE

    def test_on_leader_killed_non_leader_no_effect(self):
        """Verify: killing a non-leader unit does not trigger degradation.

        Scenario: Regular soldier killed.
        Expected: Squad stays COMBAT_READY.
        """
        mgr = SquadDegradationManager()
        soldier = _make_unit("u1", squad_id="squad_1", morale=80)
        mgr.register_squad("squad_1", ["u1"])
        mgr.on_leader_killed(soldier, [soldier])
        assert mgr.get_squad_state("squad_1") == SquadState.COMBAT_READY

    def test_on_leader_killed_applies_morale_penalty_to_survivors(self):
        """Verify: leader death applies morale penalty to surviving squad members.

        Scenario: Commander killed, soldier has morale 80.
        Expected: Soldier morale reduced by SEVERE penalty (15).
        """
        mgr = SquadDegradationManager()
        commander = _make_unit("cmdr", UnitType.COMMANDER, squad_id="squad_1")
        soldier = _make_unit("u1", squad_id="squad_1", morale=80)
        mgr.register_squad("squad_1", ["cmdr", "u1"])
        mgr.on_leader_killed(commander, [commander, soldier])
        assert soldier.morale.value == 65  # 80 - 15 (SEVERE morale_penalty)

    def test_tick_advances_recovery_and_restores_state(self):
        """Verify: ticking NCO_RECOVERY_TICKS times restores squad to DEGRADED_MILD.

        Scenario: Commander killed, NCO available, tick 30 times.
        Expected: Squad state becomes DEGRADED_MILD after recovery.
        """
        mgr = SquadDegradationManager()
        commander = _make_unit("cmdr", UnitType.COMMANDER, squad_id="squad_1")
        nco = _make_unit("nco", squad_id="squad_1", morale=80)
        mgr.register_squad("squad_1", ["cmdr", "nco"])
        mgr.on_leader_killed(commander, [commander, nco])
        assert mgr.get_squad_state("squad_1") == SquadState.DEGRADED_SEVERE
        for _ in range(30):
            mgr.tick([nco])
        assert mgr.get_squad_state("squad_1") == SquadState.DEGRADED_MILD

    def test_is_tactic_available_severe_blocks_advanced(self):
        """Verify: DEGRADED_SEVERE blocks advanced tactics, allows basic only.

        Scenario: Squad in SEVERE state.
        Expected: Advanced tactics False, basic tactics True.
        """
        mgr = SquadDegradationManager()
        commander = _make_unit("cmdr", UnitType.COMMANDER, squad_id="squad_1")
        mgr.register_squad("squad_1", ["cmdr"])
        mgr.on_leader_killed(commander, [commander])
        assert mgr.get_squad_state("squad_1") == SquadState.DEGRADED_SEVERE
        for tactic in ADVANCED_TACTICS:
            assert mgr.is_tactic_available("squad_1", tactic) is False
        for tactic in BASIC_TACTICS:
            assert mgr.is_tactic_available("squad_1", tactic) is True


class TestNCORallyBehavior:
    """Test NCO rally mechanics for panicked/routing units."""

    def test_is_nco_commander_returns_true(self):
        """Verify: commander unit is recognized as NCO.

        Scenario: Check a COMMANDER type unit.
        Expected: is_nco returns True.
        """
        rally = NCORallyBehavior()
        commander = _make_unit("cmdr", UnitType.COMMANDER)
        assert rally.is_nco(commander) is True

    def test_is_nco_squad_leader_returns_true(self):
        """Verify: squad leader is recognized as NCO.

        Scenario: Check a unit with is_squad_leader=True.
        Expected: is_nco returns True.
        """
        rally = NCORallyBehavior()
        leader = _make_unit("leader", is_squad_leader=True)
        assert rally.is_nco(leader) is True

    def test_is_nco_regular_soldier_returns_false(self):
        """Verify: regular soldier is not an NCO.

        Scenario: Check a standard infantry unit.
        Expected: is_nco returns False.
        """
        rally = NCORallyBehavior()
        soldier = _make_unit("u1")
        assert rally.is_nco(soldier) is False

    def test_is_nco_dead_unit_returns_false(self):
        """Verify: dead units are not considered NCOs.

        Scenario: Check a commander with 0 HP.
        Expected: is_nco returns False.
        """
        rally = NCORallyBehavior()
        commander = _make_unit("cmdr", UnitType.COMMANDER, hp=0)
        assert rally.is_nco(commander) is False

    def test_can_rally_high_morale_nco_returns_true(self):
        """Verify: NCO with high morale and no suppression can rally.

        Scenario: Commander with morale 80, no suppression.
        Expected: can_rally returns True.
        """
        rally = NCORallyBehavior()
        commander = _make_unit("cmdr", UnitType.COMMANDER, morale=80)
        assert rally.can_rally(commander) is True

    def test_can_rally_low_morale_nco_returns_false(self):
        """Verify: NCO with morale below threshold cannot rally.

        Scenario: Commander with morale 30 (below RALLY_MORALE_THRESHOLD=50).
        Expected: can_rally returns False.
        """
        rally = NCORallyBehavior()
        commander = _make_unit("cmdr", UnitType.COMMANDER, morale=30)
        assert rally.can_rally(commander) is False

    def test_can_rally_non_nco_returns_false(self):
        """Verify: non-NCO units cannot rally.

        Scenario: Regular soldier.
        Expected: can_rally returns False.
        """
        rally = NCORallyBehavior()
        soldier = _make_unit("u1", morale=80)
        assert rally.can_rally(soldier) is False
