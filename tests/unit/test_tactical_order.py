"""Unit tests for TacticalOrder / OrderOrigin (MC2-01)."""

from __future__ import annotations

import dataclasses

import pytest

from pycc2.domain.value_objects.tactical_order import OrderOrigin, TacticalOrder


class TestOrderOrigin:
    def test_origin_values(self):
        assert OrderOrigin.PLAYER.value == "player"
        assert OrderOrigin.COMMANDER.value == "commander"
        assert OrderOrigin.SELF.value == "self"

    def test_origin_from_string_roundtrip(self):
        assert OrderOrigin("player") is OrderOrigin.PLAYER
        assert OrderOrigin("commander") is OrderOrigin.COMMANDER

    def test_invalid_origin_string_raises(self):
        with pytest.raises(ValueError):
            OrderOrigin("enemy")


class TestTacticalOrder:
    def test_minimal_construction_defaults(self):
        order = TacticalOrder(command="defend", unit_ids=("u1",))
        assert order.command == "defend"
        assert order.unit_ids == ("u1",)
        assert order.origin is OrderOrigin.PLAYER  # origin 缺省视为 player
        assert order.params == {}
        assert order.timestamp == 0.0
        assert order.issued_tick == 0

    def test_full_construction(self):
        order = TacticalOrder(
            command="attack",
            unit_ids=("a1", "a2"),
            origin=OrderOrigin.COMMANDER,
            params={"target_id": "e1"},
            timestamp=12.5,
            issued_tick=42,
        )
        assert order.command == "attack"
        assert order.unit_ids == ("a1", "a2")
        assert order.origin is OrderOrigin.COMMANDER
        assert order.params == {"target_id": "e1"}
        assert order.timestamp == 12.5
        assert order.issued_tick == 42

    def test_is_frozen(self):
        order = TacticalOrder(command="stop", unit_ids=("u1",))
        assert dataclasses.is_dataclass(order)
        with pytest.raises(dataclasses.FrozenInstanceError):
            order.command = "move"  # type: ignore[misc]
        with pytest.raises(dataclasses.FrozenInstanceError):
            order.issued_tick = 5  # type: ignore[misc]

    def test_to_command_data_carries_params(self):
        order = TacticalOrder(
            command="set_fire_mode",
            unit_ids=("u1", "u2"),
            origin=OrderOrigin.PLAYER,
            params={"fire_mode": "hold"},
        )
        data = order.to_command_data()
        assert data["command"] == "set_fire_mode"
        assert data["unit_ids"] == ["u1", "u2"]
        assert data["fire_mode"] == "hold"

    def test_to_command_data_without_params(self):
        order = TacticalOrder(command="take_cover", unit_ids=(), origin=OrderOrigin.SELF)
        assert order.to_command_data() == {"command": "take_cover", "unit_ids": []}

    def test_equality_by_value(self):
        first = TacticalOrder(command="move", unit_ids=("u1",), params={"target": (3, 4)})
        second = TacticalOrder(command="move", unit_ids=("u1",), params={"target": (3, 4)})
        assert first == second
