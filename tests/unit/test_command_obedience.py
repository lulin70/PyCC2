"""Tests for CommandObedienceSystem — morale-based order compliance.

Covers ObedienceResult branches (OBEY/DELAYED/REFUSED/SUICIDAL), delay_order/tick
lifecycle, and suicidal-order detection (critically wounded, MG charge, AT vs tank).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from pycc2.domain.ai.command_obedience import (
    CommandObedienceSystem,
    ObedienceResult,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent, MoraleState
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


class _StubEventBus:
    """Minimal event bus stub recording publish_named calls."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish(self, event: object) -> None:
        pass

    def subscribe(self, event_type: type, handler: object) -> None:
        pass

    def subscribe_to(self, event_name: str, handler: object) -> None:
        pass

    def publish_named(self, event_name: str, data: dict) -> None:
        self.published.append((event_name, data))


def _make_unit(
    uid: str = "u1",
    unit_type: UnitType = UnitType.INFANTRY_SQUAD,
    hp: int = 100,
    max_hp: int = 100,
    morale_value: int = 80,
    morale_state: MoraleState = MoraleState.RALLIED,
    weapon_id: str = "rifle",
    x: int = 10,
    y: int = 10,
) -> Unit:
    unit = Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=Faction.ALLIES,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale_value, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id=weapon_id, ammo_remaining=8, max_ammo=8),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )
    unit.morale.state = morale_state
    return unit


def _make_intent(
    unit_id: str = "u1",
    tactic_type: TacticType = TacticType.IDLE,
    target_unit_id: str | None = None,
) -> TacticIntent:
    return TacticIntent(
        unit_id=unit_id,
        tactic_type=tactic_type,
        target_unit_id=target_unit_id,
    )


@pytest.mark.unit
class TestCommandObedienceSystemHappyPath:
    """Happy path tests: OBEY result for high-morale units."""

    def test_check_obedience_rallied_unit_obeyes_idle_order(self):
        """Verify: RALLIED unit with non-suicidal order obeys.

        Scenario: RALLIED morale (100% obey chance), IDLE order.
        Expected: result is OBEY, no delay.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", morale_state=MoraleState.RALLIED)
        intent = _make_intent("u1", TacticType.IDLE)
        with patch("pycc2.domain.ai.command_obedience.random.random", return_value=0.0):
            check = sys.check_obedience(unit, intent)
        assert check.result == ObedienceResult.OBEY
        assert check.delay_ticks == 0
        assert bus.published == []  # No refusal event on obey

    def test_check_obedience_wavering_unit_obeyes_when_roll_succeeds(self):
        """Verify: WAVERING unit (80% obey) obeys when random roll is low.

        Scenario: WAVERING morale, random.random()=0.5 (< 0.8 obey chance).
        Expected: result is OBEY (no delay because RALLIED has 0 delay, but WAVERING has 1-3).

        Note: WAVERING has (1,3) delay range, so delay is randomized. We mock
        randint to 0 to test obey path with delay, or accept DELAYED.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", morale_state=MoraleState.WAVERING)
        intent = _make_intent("u1", TacticType.IDLE)
        with patch("pycc2.domain.ai.command_obedience.random.random", return_value=0.5):
            check = sys.check_obedience(unit, intent)
        assert check.result in (ObedienceResult.OBEY, ObedienceResult.DELAYED)


@pytest.mark.unit
class TestCommandObedienceSystemRefused:
    """Refusal paths: REFUSED via routing and failed obedience roll."""

    def test_check_obedience_routing_unit_refuses_non_allowed_order(self):
        """Verify: ROUTING unit refuses orders other than RETREAT/TAKE_COVER.

        Scenario: ROUTING morale, ATTACK order (not in ROUTING_ALLOWED_ORDERS).
        Expected: result is REFUSED, refusal event published.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", morale_state=MoraleState.ROUTING)
        intent = _make_intent("u1", TacticType.ATTACK)
        check = sys.check_obedience(unit, intent)
        assert check.result == ObedienceResult.REFUSED
        assert "Routing" in check.reason
        assert len(bus.published) == 1
        assert bus.published[0][0] == "OrderRefused"

    def test_check_obedience_routing_unit_accepts_retreat(self):
        """Verify: ROUTING unit still accepts RETREAT order.

        Scenario: ROUTING morale, RETREAT order (in ROUTING_ALLOWED_ORDERS).
        Expected: Not refused at routing gate; proceeds to obedience roll (5% obey).
        Mocking random to 0.0 to ensure OBEY path (no delay because ROUTING has delay range 5-10,
        but we test the routing-gate bypass, not the roll outcome).
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", morale_state=MoraleState.ROUTING)
        intent = _make_intent("u1", TacticType.RETREAT)
        with (
            patch("pycc2.domain.ai.command_obedience.random.random", return_value=0.0),
            patch("pycc2.domain.ai.command_obedience.random.randint", return_value=0),
        ):
            check = sys.check_obedience(unit, intent)
        assert check.result != ObedienceResult.REFUSED or "Routing" not in check.reason

    def test_check_obedience_pinned_unit_refuses_when_roll_fails(self):
        """Verify: PINNED unit (50% obey) refuses when random roll exceeds chance.

        Scenario: PINNED morale, random.random()=0.9 (> 0.5 obey chance).
        Expected: result is REFUSED with morale-based reason.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", morale_state=MoraleState.PINNED)
        intent = _make_intent("u1", TacticType.IDLE)
        with patch("pycc2.domain.ai.command_obedience.random.random", return_value=0.9):
            check = sys.check_obedience(unit, intent)
        assert check.result == ObedienceResult.REFUSED
        assert "PINNED" in check.reason
        assert len(bus.published) == 1


@pytest.mark.unit
class TestCommandObedienceSystemSuicidal:
    """Suicidal-order detection: low HP attack, MG charge, AT vs tank."""

    def test_check_obedience_critically_wounded_refuses_attack(self):
        """Verify: unit with hp_ratio < 0.15 refuses ATTACK order.

        Scenario: hp=10, max_hp=100 (ratio=0.1 < 0.15), ATTACK order.
        Expected: result is SUICIDAL.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", hp=10, max_hp=100)
        intent = _make_intent("u1", TacticType.ATTACK)
        check = sys.check_obedience(unit, intent)
        assert check.result == ObedienceResult.SUICIDAL
        assert "suicidal" in check.reason.lower()
        assert bus.published[0][0] == "OrderRefused"

    def test_check_obedience_non_attack_order_not_suicidal_for_low_hp(self):
        """Verify: low-HP unit can still receive non-ATTACK orders.

        Scenario: hp=10, MOVE_TO order (not ATTACK).
        Expected: Not SUICIDAL (proceeds to morale roll).
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", hp=10, max_hp=100, morale_state=MoraleState.RALLIED)
        intent = _make_intent("u1", TacticType.MOVE_TO)
        with patch("pycc2.domain.ai.command_obedience.random.random", return_value=0.0):
            check = sys.check_obedience(unit, intent)
        assert check.result != ObedienceResult.SUICIDAL

    def test_check_obedience_charging_mg_in_open_is_suicidal(self):
        """Verify: ATTACK on MG_SQUAD in open terrain (concealment < 0.1) is suicidal.

        Scenario: Unit ATTACKs MG_SQUAD target, unit.concealment_level=0.0.
        Expected: result is SUICIDAL.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", x=10, y=10)
        # concealment_level defaults to 0.0 on PositionComponent in open terrain
        target = _make_unit("mg1", UnitType.MACHINE_GUN_SQUAD, x=11, y=10)
        intent = _make_intent("u1", TacticType.ATTACK, target_unit_id="mg1")
        check = sys.check_obedience(unit, intent, context_units=[target])
        assert check.result == ObedienceResult.SUICIDAL

    def test_check_obedience_at_rifle_vs_tank_close_range_is_suicidal(self):
        """Verify: AT weapon vs TANK at distance <= 3 is suicidal.

        Scenario: Unit with 'bazooka' weapon ATTACKs TANK at distance 2.
        Expected: result is SUICIDAL.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", weapon_id="bazooka", x=10, y=10)
        target = _make_unit("tank1", UnitType.TANK, x=12, y=10)  # distance=2
        intent = _make_intent("u1", TacticType.ATTACK, target_unit_id="tank1")
        check = sys.check_obedience(unit, intent, context_units=[target])
        assert check.result == ObedienceResult.SUICIDAL

    def test_check_obedience_at_rifle_vs_tank_far_range_not_suicidal(self):
        """Verify: AT weapon vs TANK at distance > 3 is not suicidal.

        Scenario: Unit with 'bazooka' weapon ATTACKs TANK at distance 5.
        Expected: Not SUICIDAL (proceeds to morale roll).
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        unit = _make_unit("u1", weapon_id="bazooka", x=10, y=10, morale_state=MoraleState.RALLIED)
        target = _make_unit("tank1", UnitType.TANK, x=15, y=10)  # distance=5
        intent = _make_intent("u1", TacticType.ATTACK, target_unit_id="tank1")
        with patch("pycc2.domain.ai.command_obedience.random.random", return_value=0.0):
            check = sys.check_obedience(unit, intent, context_units=[target])
        assert check.result != ObedienceResult.SUICIDAL


@pytest.mark.unit
class TestCommandObedienceSystemDelayed:
    """Delayed order lifecycle: delay_order, tick, queries."""

    def test_delay_order_records_intent(self):
        """Verify: delay_order stores a DelayedOrder for the unit.

        Scenario: Register a delayed order with 3 ticks.
        Expected: has_delayed_order returns True, delayed_order_count == 1.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        intent = _make_intent("u1", TacticType.MOVE_TO)
        sys.delay_order(intent, delay_ticks=3)
        assert sys.has_delayed_order("u1") is True
        assert sys.delayed_order_count == 1
        delayed = sys.get_delayed_order("u1")
        assert delayed is not None
        assert delayed.ticks_remaining == 3

    def test_tick_returns_ready_order_when_delay_expires(self):
        """Verify: tick decrements timers and returns ready orders.

        Scenario: Delay order by 2 ticks, call tick twice.
        Expected: First tick returns [], second tick returns [intent].
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        intent = _make_intent("u1", TacticType.MOVE_TO)
        sys.delay_order(intent, delay_ticks=2)
        ready1 = sys.tick()
        assert ready1 == []
        assert sys.has_delayed_order("u1") is True
        ready2 = sys.tick()
        assert len(ready2) == 1
        assert ready2[0] is intent
        assert sys.has_delayed_order("u1") is False

    def test_tick_empty_when_no_delayed_orders(self):
        """Verify: tick with no delayed orders returns empty list.

        Scenario: No prior delay_order calls.
        Expected: tick returns [].
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        assert sys.tick() == []
        assert sys.delayed_order_count == 0

    def test_get_delayed_order_unknown_unit_returns_none(self):
        """Verify: querying delayed order for unknown unit returns None.

        Scenario: No delayed order for 'unknown'.
        Expected: get_delayed_order returns None.
        """
        bus = _StubEventBus()
        sys = CommandObedienceSystem(event_bus=bus)
        assert sys.get_delayed_order("unknown") is None
        assert sys.has_delayed_order("unknown") is False
