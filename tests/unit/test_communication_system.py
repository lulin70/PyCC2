"""Tests for the Communication System — radio relay, delays, and comm loss.

Verify: CommunicationSystem, CommunicationRelay, CommMessage, UnitCommState.
Scenario: register units, send orders through various radio tiers, advance
ticks, detect comm loss when officers die, and check artillery availability.
Expected: delays/statuses match CC2 radio rules; messages deliver after delay;
units lose contact when out of radio range of any officer/HQ.
"""

from __future__ import annotations

from pycc2.domain.ai.communication_system import (
    HQ_RADIO_DELAY,
    HQ_RADIO_RANGE,
    MAX_RELAY_HOPS,
    OFFICER_RADIO_DELAY,
    OFFICER_RADIO_RANGE,
    RELAY_DELAY_PER_HOP,
    RUNNER_DELAY,
    SQUAD_RADIO_DELAY,
    SQUAD_RADIO_RANGE,
    WEATHER_DELAY,
    CommMessage,
    CommStatus,
    CommunicationRelay,
    CommunicationSystem,
    RadioType,
    UnitCommState,
)
from pycc2.domain.ai.tactic_intent import TacticIntent, TacticType
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.environment import EnvironmentState, TimeOfDay, WeatherCondition
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
) -> Unit:
    """Build a real Unit with all required components at the given tile."""
    return Unit(
        id=uid,
        name=f"unit_{uid}",
        faction=faction,
        unit_type=unit_type,
        health=HealthComponent(hp=hp, max_hp=max_hp),
        morale=MoraleComponent(value=morale, panic_threshold=30, rout_threshold=10),
        weapon=WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30),
        position=PositionComponent(tile_coord=TileCoord(x, y)),
        vision=VisionComponent(range_tiles=6),
    )


def _make_intent(unit_id: str = "u1") -> TacticIntent:
    """Build a simple MOVE_TO intent used as the order payload."""
    return TacticIntent(
        unit_id=unit_id,
        tactic_type=TacticType.MOVE_TO,
        priority=5,
        target_position=TileCoord(12, 12),
    )


# ---------------------------------------------------------------------------
# Radio type determination (via register_unit)
# ---------------------------------------------------------------------------


class TestRadioTypeDetermination:
    """Verify _determine_radio_type maps UnitType to the correct RadioType."""

    def test_commander_maps_to_hq_radio(self):
        """Verify: COMMANDER unit registered as RadioType.HQ and tracked as HQ."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        cs.register_unit(cmd)
        state = cs.get_unit_status("cmd")
        assert state is not None
        assert state.radio_type == RadioType.HQ

    def test_tank_maps_to_officer_radio(self):
        """Verify: TANK unit registered as RadioType.OFFICER (good vehicle radio)."""
        cs = CommunicationSystem()
        tank = _make_unit("tank", unit_type=UnitType.TANK, x=0, y=0)
        cs.register_unit(tank)
        assert cs.get_unit_status("tank").radio_type == RadioType.OFFICER

    def test_infantry_squad_maps_to_squad_radio(self):
        """Verify: INFANTRY_SQUAD registered as RadioType.SQUAD."""
        cs = CommunicationSystem()
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        cs.register_unit(inf)
        assert cs.get_unit_status("inf").radio_type == RadioType.SQUAD

    def test_all_squad_types_map_to_squad_radio(self):
        """Verify: every infantry-team type registers as RadioType.SQUAD."""
        squad_types = [
            UnitType.MACHINE_GUN_SQUAD,
            UnitType.SNIPER_TEAM,
            UnitType.MEDIC_TEAM,
            UnitType.AT_GUN_TEAM,
            UnitType.MORTAR_TEAM,
        ]
        for ut in squad_types:
            cs = CommunicationSystem()
            u = _make_unit(f"u_{ut.name}", unit_type=ut, x=0, y=0)
            cs.register_unit(u)
            assert cs.get_unit_status(u.id).radio_type == RadioType.SQUAD


# ---------------------------------------------------------------------------
# register / unregister
# ---------------------------------------------------------------------------


class TestRegisterUnregister:
    """Verify unit registration lifecycle and HQ tracking."""

    def test_register_tracks_hq_id_for_commander(self):
        """Verify: registering a COMMANDER sets the internal HQ id."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        cs.register_unit(cmd)
        # HQ id should be set so artillery/comm-loss checks can find HQ
        assert cs._hq_id == "cmd"  # noqa: SLF001

    def test_register_non_commander_does_not_set_hq(self):
        """Verify: registering a squad leaves HQ id unset."""
        cs = CommunicationSystem()
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        cs.register_unit(inf)
        assert cs._hq_id is None  # noqa: SLF001

    def test_unregister_removes_unit_state(self):
        """Verify: unregister removes the unit from the comm system."""
        cs = CommunicationSystem()
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        cs.register_unit(inf)
        cs.unregister_unit("inf")
        assert cs.get_unit_status("inf") is None

    def test_unregister_hq_clears_hq_id(self):
        """Verify: unregistering the HQ unit clears the HQ pointer."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        cs.register_unit(cmd)
        cs.unregister_unit("cmd")
        assert cs._hq_id is None  # noqa: SLF001

    def test_unregister_unknown_unit_is_noop(self):
        """Verify: unregistering an unknown id does not raise."""
        cs = CommunicationSystem()
        cs.unregister_unit("does_not_exist")  # should not raise
        assert cs.unit_states == {}

    def test_unit_states_property_returns_copy(self):
        """Verify: mutating the returned dict does not affect internal state."""
        cs = CommunicationSystem()
        cs.register_unit(_make_unit("inf", x=0, y=0))
        snapshot = cs.unit_states
        snapshot["extra"] = None
        assert "extra" not in cs.unit_states


# ---------------------------------------------------------------------------
# send_order — HQ direct (no delay)
# ---------------------------------------------------------------------------


class TestSendOrderHQDirect:
    """Verify HQ-originated orders are delivered instantly with DIRECT status."""

    def test_hq_to_squad_is_direct_zero_delay(self):
        """Verify: HQ sender produces 0-tick DIRECT message."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        msg = cs.send_order(cmd, inf, _make_intent(), all_units=[cmd, inf])
        assert msg.status == CommStatus.DIRECT
        assert msg.total_delay == HQ_RADIO_DELAY
        assert msg.relay_hops == 0
        assert msg.sender_id == "cmd"
        assert msg.recipient_id == "inf"
        assert msg.message_id == "msg_1"

    def test_send_order_auto_registers_unknown_units(self):
        """Verify: sending to an unregistered unit registers it on the fly."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        cs.send_order(cmd, inf, _make_intent(), all_units=[cmd, inf])
        assert cs.get_unit_status("cmd") is not None
        assert cs.get_unit_status("inf") is not None

    def test_send_order_enqueues_message(self):
        """Verify: a sent order appears in the message queue."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        cs.send_order(cmd, inf, _make_intent(), all_units=[cmd, inf])
        assert len(cs.message_queue) == 1


# ---------------------------------------------------------------------------
# send_order — direct radio within range
# ---------------------------------------------------------------------------


class TestSendOrderDirectRadio:
    """Verify squad/officer radios use their tier delay when in range."""

    def test_squad_to_squad_within_range_uses_squad_delay(self):
        """Verify: squad sender within 8 tiles → SQUAD_RADIO_DELAY, DIRECT."""
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=SQUAD_RADIO_RANGE, y=0)
        msg = cs.send_order(s1, s2, _make_intent(), all_units=[s1, s2])
        assert msg.status == CommStatus.DIRECT
        assert msg.total_delay == SQUAD_RADIO_DELAY
        assert msg.relay_hops == 0

    def test_tank_to_squad_within_officer_range(self):
        """Verify: TANK (officer radio) sender within 15 tiles → OFFICER delay."""
        cs = CommunicationSystem()
        tank = _make_unit("tank", unit_type=UnitType.TANK, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=OFFICER_RADIO_RANGE, y=0)
        msg = cs.send_order(tank, s2, _make_intent(), all_units=[tank, s2])
        assert msg.status == CommStatus.DIRECT
        assert msg.total_delay == OFFICER_RADIO_DELAY


# ---------------------------------------------------------------------------
# send_order — runner (out of radio range, no relay)
# ---------------------------------------------------------------------------


class TestSendOrderRunner:
    """Verify out-of-range orders with no relay use the RUNNER status."""

    def test_squad_out_of_range_no_relay_uses_runner(self):
        """Verify: squad sender beyond 8 tiles with no officer → RUNNER, delay 5."""
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=20, y=0)
        msg = cs.send_order(s1, s2, _make_intent(), all_units=[s1, s2])
        assert msg.status == CommStatus.RUNNER
        assert msg.total_delay == RUNNER_DELAY
        assert msg.relay_hops == 0


# ---------------------------------------------------------------------------
# send_order — relay through officers
# ---------------------------------------------------------------------------


class TestSendOrderRelay:
    """Verify relayed orders add per-hop delay and use RELAYED status."""

    def test_single_hop_relay_through_commander(self):
        """Verify: squad→commander→squad yields 1-hop RELAYED message.

        Sender at (0,0), recipient at (20,0) (out of 8-tile squad range),
        commander at (10,0) within 15 tiles of both endpoints.
        """
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=20, y=0)
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=0)
        msg = cs.send_order(s1, s2, _make_intent(), all_units=[s1, s2, cmd])
        assert msg.status == CommStatus.RELAYED
        assert msg.relay_hops == 1
        assert msg.total_delay == SQUAD_RADIO_DELAY + RELAY_DELAY_PER_HOP

    def test_two_hop_relay(self):
        """Verify: 2-hop relay through two commanders yields hops=2.

        Sender at (0,0), recipient at (31,0) (no single officer within 15 of
        both). Two commanders at (10,0) and (21,0) bridge the gap.
        """
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=31, y=0)
        o1 = _make_unit("o1", unit_type=UnitType.COMMANDER, x=10, y=0)
        o2 = _make_unit("o2", unit_type=UnitType.COMMANDER, x=21, y=0)
        msg = cs.send_order(s1, s2, _make_intent(), all_units=[s1, s2, o1, o2])
        assert msg.status == CommStatus.RELAYED
        assert msg.relay_hops == 2
        assert msg.total_delay == SQUAD_RADIO_DELAY + 2 * RELAY_DELAY_PER_HOP


# ---------------------------------------------------------------------------
# send_order — weather interference
# ---------------------------------------------------------------------------


class TestWeatherDelay:
    """Verify RAIN/FOG add WEATHER_DELAY ticks; CLEAR does not."""

    def test_rain_adds_weather_delay_to_hq_order(self):
        """Verify: HQ order under RAIN gains +WEATHER_DELAY ticks."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        env = EnvironmentState(time_of_day=TimeOfDay.DAY, weather=WeatherCondition.RAIN)
        msg = cs.send_order(cmd, inf, _make_intent(), [cmd, inf], environment=env)
        assert msg.total_delay == HQ_RADIO_DELAY + WEATHER_DELAY

    def test_fog_adds_weather_delay(self):
        """Verify: FOG also adds the weather delay."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        env = EnvironmentState(time_of_day=TimeOfDay.DAY, weather=WeatherCondition.FOG)
        msg = cs.send_order(cmd, inf, _make_intent(), [cmd, inf], environment=env)
        assert msg.total_delay == HQ_RADIO_DELAY + WEATHER_DELAY

    def test_clear_weather_no_extra_delay(self):
        """Verify: CLEAR weather adds nothing."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        env = EnvironmentState(time_of_day=TimeOfDay.DAY, weather=WeatherCondition.CLEAR)
        msg = cs.send_order(cmd, inf, _make_intent(), [cmd, inf], environment=env)
        assert msg.total_delay == HQ_RADIO_DELAY

    def test_no_environment_no_extra_delay(self):
        """Verify: passing environment=None adds no weather delay."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        msg = cs.send_order(cmd, inf, _make_intent(), [cmd, inf], environment=None)
        assert msg.total_delay == HQ_RADIO_DELAY


# ---------------------------------------------------------------------------
# tick — message delivery
# ---------------------------------------------------------------------------


class TestTickDelivery:
    """Verify tick() advances and delivers messages, updating recipient state."""

    def test_zero_delay_message_delivered_in_one_tick(self):
        """Verify: a 0-delay HQ message delivers on the next tick."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        intent = _make_intent()
        cs.send_order(cmd, inf, intent, [cmd, inf])
        delivered = cs.tick()
        assert len(delivered) == 1
        assert delivered[0].recipient_id == "inf"
        # Recipient state updated with the order
        state = cs.get_unit_status("inf")
        assert state.last_orders is intent
        assert state.has_contact is True
        assert state.autonomous is False
        # Message removed from the queue once delivered
        assert cs.message_queue == []

    def test_multi_tick_delivery_only_after_delay(self):
        """Verify: a 2-tick message is not delivered until 2 ticks elapse."""
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=SQUAD_RADIO_RANGE, y=0)
        cs.send_order(s1, s2, _make_intent(), [s1, s2])
        # First tick: 1 tick remaining, not yet delivered
        delivered = cs.tick()
        assert delivered == []
        assert len(cs.message_queue) == 1
        # Second tick: now delivered
        delivered = cs.tick()
        assert len(delivered) == 1
        assert cs.message_queue == []

    def test_tick_returns_empty_when_queue_empty(self):
        """Verify: tick with no pending messages returns an empty list."""
        cs = CommunicationSystem()
        assert cs.tick() == []


# ---------------------------------------------------------------------------
# check_comm_loss
# ---------------------------------------------------------------------------


class TestCheckCommLoss:
    """Verify units lose contact when out of radio range of HQ and officers."""

    def test_squad_out_of_range_loses_contact(self):
        """Verify: squad >8 tiles from HQ with no officer in range loses comms."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=20, y=0)
        cs.register_unit(cmd)
        cs.register_unit(inf)
        lost = cs.check_comm_loss([cmd, inf])
        assert "inf" in lost
        state = cs.get_unit_status("inf")
        assert state.has_contact is False
        assert state.autonomous is True

    def test_squad_within_range_keeps_contact(self):
        """Verify: squad within 8 tiles of HQ keeps contact."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=SQUAD_RADIO_RANGE, y=0)
        cs.register_unit(cmd)
        cs.register_unit(inf)
        lost = cs.check_comm_loss([cmd, inf])
        assert lost == []
        assert cs.get_unit_status("inf").has_contact is True

    def test_hq_never_loses_contact(self):
        """Verify: HQ units are skipped and never reported lost."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        cs.register_unit(cmd)
        lost = cs.check_comm_loss([cmd])
        assert lost == []
        assert cs.get_unit_status("cmd").has_contact is True

    def test_dead_unit_skipped(self):
        """Verify: dead units are not evaluated for comm loss."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        dead = _make_unit("dead", unit_type=UnitType.INFANTRY_SQUAD, x=20, y=0, hp=0)
        cs.register_unit(cmd)
        cs.register_unit(dead)
        lost = cs.check_comm_loss([cmd, dead])
        assert "dead" not in lost

    def test_squad_relayed_through_officer_keeps_contact(self):
        """Verify: squad out of HQ range but near a commander (officer) keeps contact.

        Note: _OFFICER_TYPES contains only COMMANDER, so a TANK (OFFICER radio)
        is NOT a relay officer. A second COMMANDER in all_units serves as the
        relay node. The squad is 16 tiles from HQ (out of 8-tile squad range)
        but 6 tiles from the relay commander (within 8).
        """
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)  # HQ
        relay_cmd = _make_unit("relay", unit_type=UnitType.COMMANDER, x=10, y=0)  # officer
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=16, y=0)
        cs.register_unit(cmd)  # _hq_id = "cmd"
        cs.register_unit(inf)  # relay_cmd intentionally left unregistered
        lost = cs.check_comm_loss([cmd, relay_cmd, inf])
        assert "inf" not in lost
        assert cs.get_unit_status("inf").has_contact is True


# ---------------------------------------------------------------------------
# get_comm_delay (no message created)
# ---------------------------------------------------------------------------


class TestGetCommDelay:
    """Verify get_comm_delay returns delay without enqueuing a message."""

    def test_hq_to_squad_zero_delay(self):
        """Verify: HQ sender yields 0 delay."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        assert cs.get_comm_delay(cmd, inf, [cmd, inf]) == HQ_RADIO_DELAY

    def test_squad_within_range_returns_squad_delay(self):
        """Verify: in-range squad sender returns SQUAD_RADIO_DELAY."""
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=SQUAD_RADIO_RANGE, y=0)
        assert cs.get_comm_delay(s1, s2, [s1, s2]) == SQUAD_RADIO_DELAY

    def test_out_of_range_returns_runner_delay(self):
        """Verify: out-of-range sender with no relay returns RUNNER_DELAY."""
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=20, y=0)
        assert cs.get_comm_delay(s1, s2, [s1, s2]) == RUNNER_DELAY

    def test_weather_adds_delay(self):
        """Verify: RAIN weather adds WEATHER_DELAY to the computed delay."""
        cs = CommunicationSystem()
        s1 = _make_unit("s1", unit_type=UnitType.INFANTRY_SQUAD, x=0, y=0)
        s2 = _make_unit("s2", unit_type=UnitType.INFANTRY_SQUAD, x=SQUAD_RADIO_RANGE, y=0)
        env = EnvironmentState(time_of_day=TimeOfDay.DAY, weather=WeatherCondition.RAIN)
        assert cs.get_comm_delay(s1, s2, [s1, s2], environment=env) == (
            SQUAD_RADIO_DELAY + WEATHER_DELAY
        )

    def test_get_comm_delay_does_not_enqueue_message(self):
        """Verify: get_comm_delay leaves the message queue empty."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        cs.get_comm_delay(cmd, inf, [cmd, inf])
        assert cs.message_queue == []


# ---------------------------------------------------------------------------
# is_artillery_available
# ---------------------------------------------------------------------------


class TestIsArtilleryAvailable:
    """Verify artillery call-in requires an officer in range of HQ."""

    def test_commander_can_call_artillery_when_hq_registered(self):
        """Verify: a COMMANDER caller (== HQ) is in range of itself → True."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        cs.register_unit(cmd)
        assert cs.is_artillery_available(cmd, [cmd]) is True

    def test_squad_near_commander_can_call_artillery(self):
        """Verify: squad within 8 tiles of commander (HQ) → True."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=5, y=0)
        cs.register_unit(cmd)
        cs.register_unit(inf)
        assert cs.is_artillery_available(inf, [cmd, inf]) is True

    def test_squad_with_no_officer_nearby_cannot_call(self):
        """Verify: squad with no commander in range → False."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        inf = _make_unit("inf", unit_type=UnitType.INFANTRY_SQUAD, x=20, y=0)
        cs.register_unit(cmd)
        cs.register_unit(inf)
        assert cs.is_artillery_available(inf, [cmd, inf]) is False

    def test_officer_far_from_hq_cannot_call(self):
        """Verify: a commander caller beyond 15 tiles of HQ → False.

        Note: register_unit overwrites _hq_id for every commander, so the
        caller must be LEFT UNREGISTERED to keep _hq_id pointing at the real
        HQ. The caller is a COMMANDER (in _OFFICER_TYPES) 20 tiles from HQ.
        """
        cs = CommunicationSystem()
        hq = _make_unit("hq", unit_type=UnitType.COMMANDER, x=0, y=0)
        far_cmd = _make_unit("fc", unit_type=UnitType.COMMANDER, x=20, y=0)
        cs.register_unit(hq)  # _hq_id = "hq"; far_cmd intentionally unregistered
        assert cs.is_artillery_available(far_cmd, [hq, far_cmd]) is False

    def test_no_hq_registered_returns_false_for_officer(self):
        """Verify: officer caller with no HQ registered → False."""
        cs = CommunicationSystem()
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=0, y=0)
        # Not registered → _hq_id is None
        assert cs.is_artillery_available(cmd, [cmd]) is False


# ---------------------------------------------------------------------------
# CommunicationRelay — direct unit tests
# ---------------------------------------------------------------------------


class TestCommunicationRelay:
    """Verify the relay path-finding and delay arithmetic."""

    def test_find_relay_path_no_officers_returns_empty(self):
        """Verify: with no officers the relay path is empty."""
        relay = CommunicationRelay()
        s1 = _make_unit("s1", x=0, y=0)
        s2 = _make_unit("s2", x=20, y=0)
        assert relay.find_relay_path(s1, s2, [], [s1, s2]) == []

    def test_find_relay_path_single_hop(self):
        """Verify: one officer in range of both endpoints yields a 1-node path."""
        relay = CommunicationRelay()
        s1 = _make_unit("s1", x=0, y=0)
        s2 = _make_unit("s2", x=20, y=0)
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=10, y=0)
        path = relay.find_relay_path(s1, s2, [cmd], [s1, s2, cmd])
        assert path == [cmd]

    def test_find_relay_path_two_hops(self):
        """Verify: two officers bridge a long gap with a 2-node path."""
        relay = CommunicationRelay()
        s1 = _make_unit("s1", x=0, y=0)
        s2 = _make_unit("s2", x=31, y=0)
        o1 = _make_unit("o1", unit_type=UnitType.COMMANDER, x=10, y=0)
        o2 = _make_unit("o2", unit_type=UnitType.COMMANDER, x=21, y=0)
        path = relay.find_relay_path(s1, s2, [o1, o2], [s1, s2, o1, o2])
        assert path == [o1, o2]

    def test_find_relay_path_skips_dead_officers(self):
        """Verify: dead officers are skipped during relay path search."""
        relay = CommunicationRelay()
        s1 = _make_unit("s1", x=0, y=0)
        s2 = _make_unit("s2", x=20, y=0)
        dead_cmd = _make_unit("dc", unit_type=UnitType.COMMANDER, x=10, y=0, hp=0)
        live_cmd = _make_unit("lc", unit_type=UnitType.COMMANDER, x=11, y=0)
        path = relay.find_relay_path(s1, s2, [dead_cmd, live_cmd], [s1, s2, dead_cmd, live_cmd])
        assert dead_cmd not in path
        assert path == [live_cmd]

    def test_find_relay_path_no_valid_path_returns_empty(self):
        """Verify: officers out of range yield an empty path."""
        relay = CommunicationRelay()
        s1 = _make_unit("s1", x=0, y=0)
        s2 = _make_unit("s2", x=50, y=0)
        # Single officer far from both endpoints
        cmd = _make_unit("cmd", unit_type=UnitType.COMMANDER, x=25, y=0)
        # Officer at (25,0): dist to sender 25 > 15, so no 1-hop path
        # Need a second officer for 2-hop but only one provided
        path = relay.find_relay_path(s1, s2, [cmd], [s1, s2, cmd])
        assert path == []

    def test_calculate_relay_delay_scales_with_hops(self):
        """Verify: relay delay is hops * RELAY_DELAY_PER_HOP."""
        relay = CommunicationRelay()
        assert relay.calculate_relay_delay(0) == 0
        assert relay.calculate_relay_delay(1) == RELAY_DELAY_PER_HOP
        assert relay.calculate_relay_delay(2) == 2 * RELAY_DELAY_PER_HOP
        assert relay.calculate_relay_delay(MAX_RELAY_HOPS) == MAX_RELAY_HOPS * RELAY_DELAY_PER_HOP


# ---------------------------------------------------------------------------
# CommMessage / UnitCommState dataclass behaviour
# ---------------------------------------------------------------------------


class TestCommMessageProperties:
    """Verify CommMessage.is_delivered / is_lost derived flags."""

    def test_is_delivered_true_when_ticks_remaining_zero(self):
        """Verify: a message with 0 ticks remaining is delivered."""
        msg = CommMessage(
            message_id="m1",
            sender_id="a",
            recipient_id="b",
            intent=_make_intent(),
            total_delay=0,
            ticks_remaining=0,
        )
        assert msg.is_delivered is True
        assert msg.is_lost is False

    def test_is_delivered_true_when_ticks_remaining_negative(self):
        """Verify: negative ticks_remaining also counts as delivered."""
        msg = CommMessage(
            message_id="m1",
            sender_id="a",
            recipient_id="b",
            intent=_make_intent(),
            total_delay=2,
            ticks_remaining=-1,
        )
        assert msg.is_delivered is True

    def test_is_lost_true_only_when_status_lost(self):
        """Verify: is_lost mirrors the LOST status."""
        msg = CommMessage(
            message_id="m1",
            sender_id="a",
            recipient_id="b",
            intent=_make_intent(),
            total_delay=10,
            ticks_remaining=10,
            status=CommStatus.LOST,
        )
        assert msg.is_lost is True
        assert msg.is_delivered is False

    def test_default_status_is_direct(self):
        """Verify: the default CommMessage status is DIRECT."""
        msg = CommMessage(
            message_id="m1",
            sender_id="a",
            recipient_id="b",
            intent=_make_intent(),
            total_delay=0,
            ticks_remaining=0,
        )
        assert msg.status == CommStatus.DIRECT
        assert msg.relay_hops == 0


class TestUnitCommStateProperties:
    """Verify UnitCommState.can_transmit rules."""

    def test_can_transmit_with_radio_and_contact(self):
        """Verify: a squad radio with contact can transmit."""
        state = UnitCommState(unit_id="u1", radio_type=RadioType.SQUAD)
        assert state.can_transmit is True

    def test_cannot_transmit_without_radio(self):
        """Verify: NONE radio cannot transmit even with contact."""
        state = UnitCommState(unit_id="u1", radio_type=RadioType.NONE, has_contact=True)
        assert state.can_transmit is False

    def test_cannot_transmit_without_contact(self):
        """Verify: a radio with no contact cannot transmit."""
        state = UnitCommState(unit_id="u1", radio_type=RadioType.SQUAD, has_contact=False)
        assert state.can_transmit is False

    def test_default_has_contact_true_and_no_orders(self):
        """Verify: fresh state defaults to contact=True and no last orders."""
        state = UnitCommState(unit_id="u1", radio_type=RadioType.SQUAD)
        assert state.has_contact is True
        assert state.autonomous is False
        assert state.last_orders is None


# ---------------------------------------------------------------------------
# Radio range constants sanity check
# ---------------------------------------------------------------------------


class TestRadioConstants:
    """Verify the CC2 radio constants have their documented values."""

    def test_hq_radio_is_unlimited_zero_delay(self):
        """Verify: HQ radio has unlimited range and no delay."""
        assert HQ_RADIO_RANGE >= 999
        assert HQ_RADIO_DELAY == 0

    def test_officer_and_squad_range_relationship(self):
        """Verify: officer range exceeds squad range; delays differ."""
        assert OFFICER_RADIO_RANGE > SQUAD_RADIO_RANGE
        assert OFFICER_RADIO_DELAY < SQUAD_RADIO_DELAY

    def test_relay_constants(self):
        """Verify: relay delay per hop and max hops match CC2 rules."""
        assert RELAY_DELAY_PER_HOP == 3
        assert MAX_RELAY_HOPS == 2
        assert RUNNER_DELAY == 5
        assert WEATHER_DELAY == 2
