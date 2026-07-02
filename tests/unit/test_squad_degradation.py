"""Tests for SquadDegradationManager and NCORallyBehavior.

Covers CC2-fidelity AI behavior for squad leadership loss effects
and NCO-led rally mechanics for panicked/routing units.

Real components are used (Unit, MoraleComponent) — no mocks. The optional
``is_squad_leader`` attribute (accessed via getattr in source) is set directly
on Unit instances, which the runtime permits.
"""

from __future__ import annotations

from pycc2.domain.ai.squad_degradation import (
    ADVANCED_TACTICS,
    BASIC_TACTICS,
    NCO_RECOVERY_TICKS,
    RALLY_COOLDOWN_TICKS,
    RALLY_RANGE,
    RALLY_RESTORE_MORALE,
    NCORallyBehavior,
    SquadDegradationManager,
    SquadState,
)
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers — real components, no mocks
# ---------------------------------------------------------------------------


def _make_unit(
    uid: str = "u1",
    faction: Faction = Faction.ALLIES,
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    x: int = 10,
    y: int = 10,
    hp: int = 100,
    max_hp: int = 100,
    morale: int = 80,
    squad_id: str | None = "squad_a",
    is_squad_leader: bool = False,
) -> Unit:
    u = Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
        squad_id=squad_id,
    )
    # is_squad_leader is an optional attribute accessed via getattr in source.
    u.is_squad_leader = is_squad_leader
    return u


def _kill_unit(unit: Unit) -> None:
    """Force a unit into the DEAD state without going through take_damage."""
    unit.health.hp = 0
    unit.health._update_state()
    unit.die()


# ---------------------------------------------------------------------------
# SquadDegradationManager — construction and registration
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_construct_with_empty_state(self):
        """Verify: A fresh manager has no squad records.

        Scenario: Construct SquadDegradationManager.
        Expected: get_squad_state returns COMBAT_READY for any unknown squad.
        """
        mgr = SquadDegradationManager()
        assert mgr.get_squad_state("any_squad") == SquadState.COMBAT_READY

    def test_register_squad_creates_record(self):
        """Verify: register_squad maps units to a squad and creates a COMBAT_READY record.

        Scenario: Register squad 'alpha' with units ['u1', 'u2'].
        Expected: get_squad_state('alpha') == COMBAT_READY.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1", "u2"])
        assert mgr.get_squad_state("alpha") == SquadState.COMBAT_READY

    def test_register_squad_idempotent(self):
        """Verify: Registering the same squad twice does not overwrite state.

        Scenario: Register 'alpha', degrade it, then re-register.
        Expected: State is preserved (register is idempotent for existing squads).
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        # Manually degrade by killing a leader (uses internal record)
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        mgr.on_leader_killed(leader, [leader])
        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_SEVERE

        # Re-registering should not reset the state
        mgr.register_squad("alpha", ["u1", "u2"])
        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_SEVERE

    def test_unregister_squad_removes_record(self):
        """Verify: unregister_squad clears the record and unit mappings.

        Scenario: Register 'alpha', then unregister it.
        Expected: get_squad_state returns COMBAT_READY (default for unknown).
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1", "u2"])
        mgr.unregister_squad("alpha")
        assert mgr.get_squad_state("alpha") == SquadState.COMBAT_READY

    def test_unregister_unknown_squad_is_noop(self):
        """Verify: Unregistering an unknown squad does not raise.

        Scenario: Call unregister_squad on a squad that was never registered.
        Expected: No exception, state remains COMBAT_READY.
        """
        mgr = SquadDegradationManager()
        mgr.unregister_squad("never_existed")
        assert mgr.get_squad_state("never_existed") == SquadState.COMBAT_READY


# ---------------------------------------------------------------------------
# SquadDegradationManager — modifiers and tactic gating
# ---------------------------------------------------------------------------


class TestModifiersAndTactics:
    def test_combat_ready_modifiers_are_neutral(self):
        """Verify: COMBAT_READY state has zero penalties.

        Scenario: Fresh squad in COMBAT_READY.
        Expected: accuracy_modifier=1.0, reaction_delay_multiplier=1.0.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        assert mgr.get_accuracy_modifier("alpha") == 1.0
        assert mgr.get_reaction_delay_multiplier("alpha") == 1.0

    def test_combat_ready_allows_all_tactics(self):
        """Verify: COMBAT_READY squads can use all tactics.

        Scenario: Check an advanced and a basic tactic for a fresh squad.
        Expected: Both return True.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        assert mgr.is_tactic_available("alpha", "FLANKING") is True
        assert mgr.is_tactic_available("alpha", "FIRE_CONCENTRATION") is True

    def test_degraded_severe_blocks_advanced_tactics(self):
        """Verify: DEGRADED_SEVERE squads cannot use advanced tactics.

        Scenario: Squad enters SEVERE degradation (commander killed).
        Expected: FLANKING (advanced) is blocked; FIRE_CONCENTRATION (basic) allowed.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1", "cmd"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        mgr.on_leader_killed(leader, [leader])

        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_SEVERE
        assert mgr.is_tactic_available("alpha", "FLANKING") is False
        assert mgr.is_tactic_available("alpha", "FIRE_CONCENTRATION") is True

    def test_get_available_tactics_severe_returns_basic_only(self):
        """Verify: SEVERE squads are limited to BASIC_TACTICS.

        Scenario: Squad in SEVERE state.
        Expected: get_available_tactics returns BASIC_TACTICS (copy, not the original).
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        mgr.on_leader_killed(leader, [leader])

        tactics = mgr.get_available_tactics("alpha")
        assert tactics == BASIC_TACTICS
        # Should be a copy, not the module-level set
        tactics.add("HACK")
        assert "HACK" not in BASIC_TACTICS

    def test_get_available_tactics_combat_ready_returns_all(self):
        """Verify: COMBAT_READY squads get ADVANCED | BASIC tactics.

        Scenario: Fresh squad.
        Expected: get_available_tactics returns the union of advanced and basic.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        tactics = mgr.get_available_tactics("alpha")
        assert tactics == ADVANCED_TACTICS | BASIC_TACTICS

    def test_accuracy_modifier_severe_is_half(self):
        """Verify: DEGRADED_SEVERE imposes a 50% accuracy penalty.

        Scenario: Squad in SEVERE state (accuracy_penalty=0.50).
        Expected: accuracy_modifier == 0.5.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        mgr.on_leader_killed(leader, [leader])

        assert mgr.get_accuracy_modifier("alpha") == 0.5

    def test_reaction_delay_severe_doubles(self):
        """Verify: DEGRADED_SEVERE imposes 100% reaction delay (2x multiplier).

        Scenario: Squad in SEVERE state (reaction_delay_pct=1.00).
        Expected: reaction_delay_multiplier == 2.0.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        mgr.on_leader_killed(leader, [leader])

        assert mgr.get_reaction_delay_multiplier("alpha") == 2.0


# ---------------------------------------------------------------------------
# SquadDegradationManager — on_leader_killed
# ---------------------------------------------------------------------------


class TestOnLeaderKilled:
    def test_platoon_commander_killed_causes_severe(self):
        """Verify: Killing a platoon commander (UnitType.COMMANDER) → SEVERE.

        Scenario: Commander of squad 'alpha' is killed.
        Expected: squad state == DEGRADED_SEVERE.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd", "u1", "u2"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        members = [leader, _make_unit("u1", squad_id="alpha")]

        mgr.on_leader_killed(leader, members)

        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_SEVERE

    def test_squad_leader_killed_causes_moderate(self):
        """Verify: Killing a squad leader (is_squad_leader=True) → MODERATE.

        Scenario: Squad leader of squad 'bravo' is killed.
        Expected: squad state == DEGRADED_MODERATE.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("bravo", ["sl", "u1"])
        leader = _make_unit("sl", squad_id="bravo", is_squad_leader=True)
        members = [leader, _make_unit("u1", squad_id="bravo")]

        mgr.on_leader_killed(leader, members)

        assert mgr.get_squad_state("bravo") == SquadState.DEGRADED_MODERATE

    def test_non_leader_killed_does_not_degrade(self):
        """Verify: Killing a regular unit does not change squad state.

        Scenario: A regular infantry unit (not a leader) is killed.
        Expected: squad state remains COMBAT_READY.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1", "u2"])
        regular = _make_unit("u1", squad_id="alpha", is_squad_leader=False)
        members = [regular, _make_unit("u2", squad_id="alpha")]

        mgr.on_leader_killed(regular, members)

        assert mgr.get_squad_state("alpha") == SquadState.COMBAT_READY

    def test_leader_killed_applies_morale_penalty_to_survivors(self):
        """Verify: When a leader dies, surviving squad members lose morale.

        Scenario: Commander killed; squad has one survivor with morale 80.
        Expected: Survivor's morale drops by morale_penalty (15 for SEVERE).
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd", "u1"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        survivor = _make_unit("u1", squad_id="alpha", morale=80)
        members = [leader, survivor]

        mgr.on_leader_killed(leader, members)

        # SEVERE state has morale_penalty=15
        assert survivor.morale.value == 80 - 15

    def test_leader_killed_with_no_squad_id_is_noop(self):
        """Verify: A killed unit with squad_id=None does not trigger degradation.

        Scenario: Commander with squad_id=None is killed.
        Expected: No exception, no state change.
        """
        mgr = SquadDegradationManager()
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id=None)

        mgr.on_leader_killed(leader, [leader])

        # No squad registered — nothing should happen
        assert mgr.get_squad_state("any") == SquadState.COMBAT_READY

    def test_leader_killed_with_available_nco_starts_recovery(self):
        """Verify: When an NCO is available, recovery timer starts.

        Scenario: Commander killed; a combat-effective squad member can take over.
        Expected: pending_nco_id is set, recovery_ticks_remaining == NCO_RECOVERY_TICKS.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd", "nco"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        nco = _make_unit("nco", squad_id="alpha", morale=80)
        members = [leader, nco]

        mgr.on_leader_killed(leader, members)

        record = mgr._squad_records["alpha"]
        assert record.pending_nco_id == "nco"
        assert record.recovery_ticks_remaining == NCO_RECOVERY_TICKS

    def test_leader_killed_with_no_nco_available(self):
        """Verify: When no NCO is available, recovery does not start.

        Scenario: Commander killed; the only survivor is also a commander (skipped).
        Expected: pending_nco_id is None, recovery_ticks_remaining == 0.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd1", "cmd2"])
        leader = _make_unit("cmd1", unit_type=UnitType.COMMANDER, squad_id="alpha")
        # Another commander — _find_available_nco skips COMMANDER type
        other_cmd = _make_unit("cmd2", unit_type=UnitType.COMMANDER, squad_id="alpha")
        members = [leader, other_cmd]

        mgr.on_leader_killed(leader, members)

        record = mgr._squad_records["alpha"]
        assert record.pending_nco_id is None
        assert record.recovery_ticks_remaining == 0


# ---------------------------------------------------------------------------
# SquadDegradationManager — tick recovery
# ---------------------------------------------------------------------------


class TestTickRecovery:
    def test_tick_advances_recovery_and_promotes_nco(self):
        """Verify: After NCO_RECOVERY_TICKS ticks, NCO assumes command → DEGRADED_MILD.

        Scenario: Commander killed, NCO available. Tick NCO_RECOVERY_TICKS times.
        Expected: state == DEGRADED_MILD, pending_nco_id cleared.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd", "nco"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        nco = _make_unit("nco", squad_id="alpha", morale=80)
        mgr.on_leader_killed(leader, [leader, nco])

        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_SEVERE

        # Tick until recovery completes
        for _ in range(NCO_RECOVERY_TICKS):
            mgr.tick([nco])

        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_MILD
        record = mgr._squad_records["alpha"]
        assert record.pending_nco_id is None

    def test_tick_recovery_aborts_if_nco_dies(self):
        """Verify: If the NCO dies before assuming command, recovery does not promote.

        Scenario: NCO dies mid-recovery. Tick until timer expires.
        Expected: state remains SEVERE (not promoted to MILD), pending_nco_id cleared.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd", "nco"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        nco = _make_unit("nco", squad_id="alpha", morale=80)
        mgr.on_leader_killed(leader, [leader, nco])

        # Kill the NCO before recovery completes
        _kill_unit(nco)

        # Tick until timer expires
        for _ in range(NCO_RECOVERY_TICKS):
            mgr.tick([nco])

        # State should remain SEVERE (NCO died before assuming command)
        assert mgr.get_squad_state("alpha") == SquadState.DEGRADED_SEVERE
        record = mgr._squad_records["alpha"]
        assert record.pending_nco_id is None

    def test_tick_severe_squad_finds_new_nco(self):
        """Verify: A SEVERE squad with no pending NCO finds one during tick.

        Scenario: Squad is SEVERE with no pending NCO. A combat-effective unit exists.
        Expected: After tick, pending_nco_id is set and recovery timer starts.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["cmd", "u1"])
        leader = _make_unit("cmd", unit_type=UnitType.COMMANDER, squad_id="alpha")
        # No NCO available at kill time (only the commander)
        mgr.on_leader_killed(leader, [leader])

        record = mgr._squad_records["alpha"]
        assert record.pending_nco_id is None

        # A new unit arrives (e.g., reinforcement) — tick should find it
        new_nco = _make_unit("reinforcement", squad_id="alpha", morale=80)
        mgr.tick([new_nco])

        record = mgr._squad_records["alpha"]
        assert record.pending_nco_id == "reinforcement"
        assert record.recovery_ticks_remaining == NCO_RECOVERY_TICKS

    def test_tick_with_no_recovery_in_progress_is_noop(self):
        """Verify: tick on a COMBAT_READY squad does nothing.

        Scenario: Fresh squad with no pending recovery.
        Expected: No exception, state remains COMBAT_READY.
        """
        mgr = SquadDegradationManager()
        mgr.register_squad("alpha", ["u1"])
        mgr.tick([_make_unit("u1", squad_id="alpha")])
        assert mgr.get_squad_state("alpha") == SquadState.COMBAT_READY


# ---------------------------------------------------------------------------
# NCORallyBehavior — is_nco and can_rally
# ---------------------------------------------------------------------------


class TestIsNcoAndCanRally:
    def test_commander_is_nco(self):
        """Verify: A COMMANDER unit type is recognized as an NCO.

        Scenario: A living commander unit.
        Expected: is_nco returns True.
        """
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, morale=80)
        behavior = NCORallyBehavior()
        assert behavior.is_nco(nco) is True

    def test_squad_leader_is_nco(self):
        """Verify: A unit with is_squad_leader=True is recognized as an NCO.

        Scenario: A living squad leader.
        Expected: is_nco returns True.
        """
        nco = _make_unit("sl", is_squad_leader=True, morale=80)
        behavior = NCORallyBehavior()
        assert behavior.is_nco(nco) is True

    def test_regular_unit_is_not_nco(self):
        """Verify: A regular infantry unit is not an NCO.

        Scenario: A living infantry squad member.
        Expected: is_nco returns False.
        """
        regular = _make_unit("u1", morale=80)
        behavior = NCORallyBehavior()
        assert behavior.is_nco(regular) is False

    def test_dead_commander_is_not_nco(self):
        """Verify: A dead commander is not considered an active NCO.

        Scenario: A commander that has been killed.
        Expected: is_nco returns False.
        """
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, morale=80)
        _kill_unit(nco)
        behavior = NCORallyBehavior()
        assert behavior.is_nco(nco) is False

    def test_can_rally_true_for_healthy_commander(self):
        """Verify: A high-morale, unsuppressed commander can rally.

        Scenario: Commander with morale=80, suppression=NONE.
        Expected: can_rally returns True.
        """
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, morale=80)
        behavior = NCORallyBehavior()
        assert behavior.can_rally(nco) is True

    def test_can_rally_false_for_low_morale_nco(self):
        """Verify: An NCO with morale below threshold cannot rally.

        Scenario: Commander with morale=40 (< RALLY_MORALE_THRESHOLD=50).
        Expected: can_rally returns False.
        """
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, morale=40)
        behavior = NCORallyBehavior()
        assert behavior.can_rally(nco) is False

    def test_can_rally_false_during_cooldown(self):
        """Verify: An NCO on rally cooldown cannot rally again.

        Scenario: NCO rallies a unit (starts cooldown); immediately can_rally returns False.
        Expected: can_rally returns False during cooldown.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, morale=80, x=10, y=10)
        target = _make_unit("panic", morale=10, x=10, y=10)
        target.morale.start_routing()

        assert behavior.rally_unit(nco, target) is True
        assert behavior.can_rally(nco) is False
        assert behavior.get_cooldown("cmd") == RALLY_COOLDOWN_TICKS

    def test_can_rally_false_for_non_nco(self):
        """Verify: A non-NCO unit cannot rally.

        Scenario: Regular infantry unit with high morale.
        Expected: can_rally returns False.
        """
        regular = _make_unit("u1", morale=80)
        behavior = NCORallyBehavior()
        assert behavior.can_rally(regular) is False


# ---------------------------------------------------------------------------
# NCORallyBehavior — find_panicked_units
# ---------------------------------------------------------------------------


class TestFindPanickedUnits:
    def test_finds_broken_and_routing_units_in_range(self):
        """Verify: find_panicked_units returns BROKEN/ROUTING friendlies within sense range.

        Scenario: NCO at (10,10); broken unit at (12,10) dist=2; routing at (15,10) dist=5.
        Expected: Both are returned (within RALLY_SENSE_RANGE=8).
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        broken = _make_unit("b1", x=12, y=10, morale=15)  # BROKEN state
        routing = _make_unit("r1", x=15, y=10, morale=5)
        routing.morale.start_routing()

        panicked = behavior.find_panicked_units(nco, [nco, broken, routing])

        ids = {u.id for u in panicked}
        assert ids == {"b1", "r1"}

    def test_excludes_enemy_units(self):
        """Verify: find_panicked_units only returns same-faction units.

        Scenario: NCO ALLIES; broken AXIS unit nearby.
        Expected: Enemy unit is excluded.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, faction=Faction.ALLIES, x=10, y=10)
        enemy_broken = _make_unit("eb", faction=Faction.AXIS, x=12, y=10, morale=15)

        panicked = behavior.find_panicked_units(nco, [nco, enemy_broken])

        assert panicked == []

    def test_excludes_units_beyond_sense_range(self):
        """Verify: Units beyond sense_range are not returned.

        Scenario: NCO at (10,10); broken unit at (20,10) dist=10 > sense_range=8.
        Expected: Empty list.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        far_broken = _make_unit("far", x=20, y=10, morale=15)

        panicked = behavior.find_panicked_units(nco, [nco, far_broken])

        assert panicked == []

    def test_excludes_dead_units(self):
        """Verify: Dead panicked units are not returned.

        Scenario: A broken unit that is also dead.
        Expected: Not included in results.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        dead_broken = _make_unit("dead", x=12, y=10, morale=15)
        _kill_unit(dead_broken)

        panicked = behavior.find_panicked_units(nco, [nco, dead_broken])

        assert panicked == []


# ---------------------------------------------------------------------------
# NCORallyBehavior — rally_unit
# ---------------------------------------------------------------------------


class TestRallyUnit:
    def test_rally_restores_morale_and_state(self):
        """Verify: rally_unit restores a panicked target to WAVERING with RALLY_RESTORE_MORALE.

        Scenario: NCO rallies a routing unit within RALLY_RANGE.
        Expected: target.morale.value == RALLY_RESTORE_MORALE, state == WAVERING,
                  suppression == 1, returns True.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        target = _make_unit("panic", x=11, y=10, morale=5)
        target.morale.start_routing()

        result = behavior.rally_unit(nco, target)

        assert result is True
        assert target.morale.value == RALLY_RESTORE_MORALE
        assert target.morale.state == MoraleState.WAVERING
        assert target.morale.suppression == 1

    def test_rally_out_of_range_returns_false(self):
        """Verify: rally_unit fails when target is beyond RALLY_RANGE.

        Scenario: NCO at (10,10); target at (16,10) dist=6 > RALLY_RANGE=5.
        Expected: Returns False, target morale unchanged.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        target = _make_unit("far_panic", x=16, y=10, morale=5)
        target.morale.start_routing()

        result = behavior.rally_unit(nco, target)

        assert result is False
        assert target.morale.state == MoraleState.ROUTING

    def test_rally_non_panicked_target_returns_false(self):
        """Verify: rally_unit fails when target is not BROKEN or ROUTING.

        Scenario: Target is RALLIED (morale=80).
        Expected: Returns False.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        target = _make_unit("ok", x=11, y=10, morale=80)  # RALLIED, not panicked

        result = behavior.rally_unit(nco, target)

        assert result is False

    def test_rally_starts_cooldown(self):
        """Verify: After a successful rally, the NCO enters a cooldown.

        Scenario: NCO rallies a unit.
        Expected: get_cooldown(nco.id) == RALLY_COOLDOWN_TICKS.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        target = _make_unit("panic", x=11, y=10, morale=5)
        target.morale.start_routing()

        behavior.rally_unit(nco, target)

        assert behavior.get_cooldown("cmd") == RALLY_COOLDOWN_TICKS

    def test_rally_by_non_nco_returns_false(self):
        """Verify: A non-NCO unit cannot rally.

        Scenario: Regular infantry attempts to rally a panicked unit.
        Expected: Returns False.
        """
        behavior = NCORallyBehavior()
        regular = _make_unit("u1", x=10, y=10, morale=80)
        target = _make_unit("panic", x=11, y=10, morale=5)
        target.morale.start_routing()

        result = behavior.rally_unit(regular, target)

        assert result is False


# ---------------------------------------------------------------------------
# NCORallyBehavior — should_move_toward_panicked
# ---------------------------------------------------------------------------


class TestShouldMoveTowardPanicked:
    def test_returns_none_when_panicked_in_range(self):
        """Verify: When a panicked unit is already in RALLY_RANGE, returns None.

        Scenario: NCO at (10,10); broken unit at (12,10) dist=2 <= RALLY_RANGE=5.
        Expected: None (no need to move).
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        in_range = _make_unit("in", x=12, y=10, morale=15)

        result = behavior.should_move_toward_panicked(nco, [nco, in_range])

        assert result is None

    def test_returns_nearest_when_all_out_of_range(self):
        """Verify: When all panicked units are out of RALLY_RANGE, returns the nearest.

        Scenario: NCO at (10,10); broken units at (16,10) dist=6 and (18,10) dist=8.
        Expected: Returns the unit at (16,10) (nearest).
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        nearer = _make_unit("near", x=16, y=10, morale=15)
        farther = _make_unit("far", x=18, y=10, morale=15)

        result = behavior.should_move_toward_panicked(nco, [nco, nearer, farther])

        assert result is not None
        assert result.id == "near"

    def test_returns_none_when_no_panicked_units(self):
        """Verify: When no panicked units exist, returns None.

        Scenario: NCO with only healthy friendlies nearby.
        Expected: None.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        healthy = _make_unit("ok", x=12, y=10, morale=80)

        result = behavior.should_move_toward_panicked(nco, [nco, healthy])

        assert result is None

    def test_returns_none_when_nco_on_cooldown(self):
        """Verify: When the NCO is on cooldown, returns None.

        Scenario: NCO has an active rally cooldown.
        Expected: None (cannot rally, so no point moving).
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        # Put NCO on cooldown by rallying a unit
        rally_target = _make_unit("rt", x=11, y=10, morale=5)
        rally_target.morale.start_routing()
        behavior.rally_unit(nco, rally_target)

        # A new panicked unit appears out of range
        new_panic = _make_unit("np", x=17, y=10, morale=10)

        result = behavior.should_move_toward_panicked(nco, [nco, new_panic])

        assert result is None


# ---------------------------------------------------------------------------
# NCORallyBehavior — tick cooldown
# ---------------------------------------------------------------------------


class TestRallyTickCooldown:
    def test_tick_decrements_cooldown(self):
        """Verify: tick decrements the rally cooldown by one.

        Scenario: NCO on cooldown (60 ticks). Tick once.
        Expected: get_cooldown returns 59.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        target = _make_unit("panic", x=11, y=10, morale=5)
        target.morale.start_routing()
        behavior.rally_unit(nco, target)

        behavior.tick()

        assert behavior.get_cooldown("cmd") == RALLY_COOLDOWN_TICKS - 1

    def test_tick_clears_expired_cooldown(self):
        """Verify: After cooldown expires, the record is removed.

        Scenario: Tick RALLY_COOLDOWN_TICKS times.
        Expected: get_cooldown returns 0, can_rally returns True again.
        """
        behavior = NCORallyBehavior()
        nco = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=10, morale=80)
        target = _make_unit("panic", x=11, y=10, morale=5)
        target.morale.start_routing()
        behavior.rally_unit(nco, target)

        for _ in range(RALLY_COOLDOWN_TICKS):
            behavior.tick()

        assert behavior.get_cooldown("cmd") == 0
        assert behavior.can_rally(nco) is True

    def test_tick_with_no_cooldowns_is_noop(self):
        """Verify: tick on a behavior with no active cooldowns does nothing.

        Scenario: Fresh behavior, no rallies performed.
        Expected: No exception.
        """
        behavior = NCORallyBehavior()
        behavior.tick()
        assert behavior.get_cooldown("anyone") == 0


# ---------------------------------------------------------------------------
# Module invariants
# ---------------------------------------------------------------------------


class TestModuleInvariants:
    def test_squad_state_has_four_tiers(self):
        """Verify: SquadState enum has the four degradation tiers."""
        states = {
            SquadState.COMBAT_READY,
            SquadState.DEGRADED_MILD,
            SquadState.DEGRADED_MODERATE,
            SquadState.DEGRADED_SEVERE,
        }
        assert len(states) == 4

    def test_advanced_and_basic_tactics_are_disjoint(self):
        """Verify: ADVANCED_TACTICS and BASIC_TACTICS share no elements."""
        assert ADVANCED_TACTICS.isdisjoint(BASIC_TACTICS)

    def test_rally_constants_have_expected_values(self):
        """Verify: Rally-related constants match the CC2 design values."""
        assert RALLY_RANGE == 5
        assert RALLY_RESTORE_MORALE == 40
        assert RALLY_COOLDOWN_TICKS == 60
        assert NCO_RECOVERY_TICKS == 30
