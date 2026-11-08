"""Unit tests for AttackLineSystem (CC2-style attack line evaluation).

Supplementary coverage tests: AttackLineSystem is a direct dependency of
UIOverlayRenderer, so its pure state machine and hit-probability logic are
exercised here with lightweight fake units.
"""

from __future__ import annotations

import time
from types import SimpleNamespace

import pytest

from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.morale_system import MoraleSystem
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.input.attack_line_system import (
    AttackLineStatus,
    AttackLineSystem,
    AttackTarget,
)


def _unit(
    unit_id: str = "u1",
    faction: str = "ALLIES",
    x: float = 0.0,
    y: float = 0.0,
    alive: bool = True,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=unit_id,
        faction=SimpleNamespace(name=faction),
        is_alive=alive,
        position=SimpleNamespace(pixel_position=Vec2(x, y)),
    )


def _attacker(
    weapon_range: float = 300,
    captured: bool = False,
    fatigue: float = 0,
    experience: int = 0,
    move_mode: str | None = None,
    morale=None,
    weapon_missing: bool = False,
) -> SimpleNamespace:
    weapon = (
        None if weapon_missing else SimpleNamespace(max_range=weapon_range, is_captured=captured)
    )
    return SimpleNamespace(
        position=SimpleNamespace(
            tile_coord=TileCoord(0, 0),
            pixel_position=Vec2(0, 0),
        ),
        weapon=weapon,
        fatigue=fatigue,
        experience_level=experience,
        move_mode=move_mode,
        morale=morale,
    )


# ===========================================================================
# update_mouse_position
# ===========================================================================


@pytest.mark.unit
class TestUpdateMousePosition:
    def test_inactive_returns_plain_target(self):
        system = AttackLineSystem()

        target = system.update_mouse_position((10, 20), Vec2(30, 40), [], "ALLIES")

        assert target == AttackTarget(position=Vec2(30, 40))
        assert system.state.target is None

    def test_active_without_source_returns_plain_target(self):
        system = AttackLineSystem()
        system.state.active = True
        system.state.source_position = None

        target = system.update_mouse_position((10, 20), Vec2(30, 40), [], "ALLIES")

        assert target.position == Vec2(30, 40)

    def test_hovering_enemy_unit_creates_unit_target(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        enemy = _unit("enemy", faction="AXIS", x=10, y=10)

        target = system.update_mouse_position((0, 0), Vec2(10, 10), [enemy], "ALLIES")

        assert target.unit_id == "enemy"
        assert target.is_ground_target is False
        assert target.position == Vec2(10, 10)
        assert target.distance == pytest.approx((10**2 + 10**2) ** 0.5)
        assert system.state.target is target

    def test_hovering_friendly_unit_creates_ground_target(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        friendly = _unit("ally", faction="ALLIES", x=5, y=5)

        target = system.update_mouse_position((0, 0), Vec2(5, 5), [friendly], "ALLIES")

        assert target.unit_id is None
        assert target.is_ground_target is True
        assert target.position == Vec2(5, 5)

    def test_dead_enemy_is_ignored(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        enemy = _unit("enemy", faction="AXIS", x=5, y=5, alive=False)

        target = system.update_mouse_position((0, 0), Vec2(5, 5), [enemy], "ALLIES")

        assert target.unit_id is None
        assert target.is_ground_target is True

    def test_enemy_outside_hover_radius_is_ground_target(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        enemy = _unit("enemy", faction="AXIS", x=100, y=100)

        target = system.update_mouse_position((0, 0), Vec2(0, 0), [enemy], "ALLIES")

        assert target.unit_id is None

    def test_faction_enum_is_accepted(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        enemy = _unit("enemy", faction=Faction.AXIS.name, x=5, y=5)

        target = system.update_mouse_position((0, 0), Vec2(5, 5), [enemy], Faction.ALLIES)

        assert target.unit_id == "enemy"


# ===========================================================================
# confirm / cancel / lookup
# ===========================================================================


@pytest.mark.unit
class TestConfirmAndCancel:
    def test_confirm_with_source_stores_attack_and_cancels(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        target = AttackTarget(position=Vec2(50, 50), unit_id="enemy")

        system.confirm_attack(target)

        assert system._confirmed_attacks["u1"] is target
        assert system.state.confirmed_target is target
        assert system.state.active is False
        assert system.state.source_unit_id is None

    def test_confirm_without_source_does_not_store(self):
        system = AttackLineSystem()
        target = AttackTarget(position=Vec2(50, 50))

        system.confirm_attack(target)

        assert system._confirmed_attacks == {}

    def test_confirm_stores_source_for_confirmed_attack(self):
        """GAP-11: the attacker position must be kept for line rendering."""
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(10, 20))
        system.confirm_attack(AttackTarget(position=Vec2(50, 50), unit_id="enemy"))

        source = system.get_confirmed_source("u1")
        assert source is not None
        assert (source.x, source.y) == (10, 20)

    def test_remove_attack_clears_source(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(10, 20))
        system.confirm_attack(AttackTarget(position=Vec2(50, 50), unit_id="enemy"))

        system.remove_attack("u1")

        assert system.get_confirmed_source("u1") is None
        assert system.get_confirmed_attack("u1") is None

    def test_update_tracking_refreshes_attacker_source(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(10, 20))
        system.confirm_attack(AttackTarget(position=Vec2(50, 50), unit_id="enemy"))
        attacker = _unit("u1", faction=Faction.ALLIES.name, x=30, y=40)
        enemy = _unit("enemy", faction=Faction.AXIS.name, x=50, y=50)

        system.update_tracking([attacker, enemy])

        source = system.get_confirmed_source("u1")
        assert source is not None
        assert (source.x, source.y) == (30, 40)

    def test_get_confirmed_attack(self):
        system = AttackLineSystem()
        target = AttackTarget(position=Vec2(1, 2))
        system._confirmed_attacks["u1"] = target

        assert system.get_confirmed_attack("u1") is target
        assert system.get_confirmed_attack("missing") is None

    def test_cancel_resets_state(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(10, 10))
        system.state.current_mouse_pos = (1, 2)
        system.state.current_world_pos = Vec2(3, 4)
        system.state.target = AttackTarget(position=Vec2(5, 5))

        system.cancel()

        assert system.state.active is False
        assert system.state.source_unit_id is None
        assert system.state.source_position is None
        assert system.state.current_mouse_pos is None
        assert system.state.current_world_pos is None
        assert system.state.target is None


# ===========================================================================
# update_tracking
# ===========================================================================


@pytest.mark.unit
class TestUpdateTracking:
    def test_updates_position_of_alive_target_unit(self):
        system = AttackLineSystem()
        target = AttackTarget(position=Vec2(0, 0), unit_id="enemy")
        system._confirmed_attacks["u1"] = target
        enemy = _unit("enemy", faction="AXIS", x=42, y=43)

        system.update_tracking([enemy])

        assert target.position == Vec2(42, 43)

    def test_removes_attack_when_target_unit_missing(self):
        system = AttackLineSystem()
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(0, 0), unit_id="enemy")

        system.update_tracking([])

        assert system._confirmed_attacks == {}

    def test_removes_attack_when_target_unit_dead(self):
        system = AttackLineSystem()
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(0, 0), unit_id="enemy")
        enemy = _unit("enemy", faction="AXIS", alive=False)

        system.update_tracking([enemy])

        assert system._confirmed_attacks == {}

    def test_ground_target_is_ignored(self):
        system = AttackLineSystem()
        target = AttackTarget(position=Vec2(7, 7), unit_id=None, is_ground_target=True)
        system._confirmed_attacks["u1"] = target

        system.update_tracking([_unit("enemy", faction="AXIS")])

        assert system._confirmed_attacks["u1"] is target
        assert target.position == Vec2(7, 7)


# ===========================================================================
# evaluate_attack
# ===========================================================================


@pytest.mark.unit
class TestEvaluateAttack:
    def test_no_weapon_returns_no_target(self):
        system = AttackLineSystem()
        attacker = _attacker(weapon_missing=True)
        target = AttackTarget(position=Vec2(10, 0), distance=10)

        assert system.evaluate_attack(attacker, target) is AttackLineStatus.NO_TARGET

    def test_out_of_range(self):
        system = AttackLineSystem()
        attacker = _attacker(weapon_range=50)
        target = AttackTarget(position=Vec2(100, 0), distance=100)

        assert system.evaluate_attack(attacker, target) is AttackLineStatus.OUT_OF_RANGE
        assert target.weapon_range == 50

    def test_blocked_by_line_of_sight(self):
        system = AttackLineSystem()
        attacker = _attacker()
        target = AttackTarget(position=Vec2(10, 0), distance=10)
        los = SimpleNamespace(check_los=lambda from_coord, to_coord: (False, None))

        status = system.evaluate_attack(attacker, target, game_map=object(), los_system=los)

        assert status is AttackLineStatus.BLOCKED

    def test_los_failure_falls_back_to_hit_probability(self):
        system = AttackLineSystem()
        attacker = _attacker()
        target = AttackTarget(position=Vec2(10, 0), distance=10)

        def _broken_los(from_coord, to_coord):
            raise ValueError("bad LOS input")

        los = SimpleNamespace(check_los=_broken_los)

        status = system.evaluate_attack(attacker, target, game_map=object(), los_system=los)

        assert status in {
            AttackLineStatus.HIT_HIGH,
            AttackLineStatus.HIT_MODERATE,
            AttackLineStatus.HIT_LOW,
            AttackLineStatus.HIT_IMPOSSIBLE,
        }

    def test_in_range_clear_los_returns_high_hit(self):
        system = AttackLineSystem()
        attacker = _attacker()
        target = AttackTarget(position=Vec2(10, 0), distance=10)

        assert system.evaluate_attack(attacker, target) is AttackLineStatus.HIT_HIGH


# ===========================================================================
# calculate_hit_probability
# ===========================================================================


@pytest.mark.unit
class TestCalculateHitProbability:
    def test_zero_weapon_range_returns_zero(self):
        attacker = _attacker(weapon_range=0)
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        assert AttackLineSystem.calculate_hit_probability(attacker, target) == 0.0

    def test_optimal_range_returns_ninety_percent(self):
        attacker = _attacker(weapon_range=300)
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        assert AttackLineSystem.calculate_hit_probability(attacker, target) == pytest.approx(0.9)

    def test_maximum_range_returns_twenty_percent(self):
        attacker = _attacker(weapon_range=300)
        target = AttackTarget(position=Vec2(0, 0), distance=300)

        assert AttackLineSystem.calculate_hit_probability(attacker, target) == pytest.approx(0.2)

    def test_cover_and_concealment_penalty(self):
        attacker = _attacker()
        target = AttackTarget(position=Vec2(0, 0), distance=0)
        game_map = SimpleNamespace(
            get_tile=lambda tx, ty: SimpleNamespace(cover_level=1, concealment=1)
        )

        probability = AttackLineSystem.calculate_hit_probability(attacker, target, game_map)

        assert probability == pytest.approx(0.65)

    def test_tile_lookup_failure_is_ignored(self):
        attacker = _attacker()
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        def _broken_get_tile(tx, ty):
            raise ValueError("bad tile")

        game_map = SimpleNamespace(get_tile=_broken_get_tile)

        assert AttackLineSystem.calculate_hit_probability(
            attacker, target, game_map
        ) == pytest.approx(0.9)

    @pytest.mark.parametrize(
        ("fatigue", "expected"),
        [(0, 0.9), (41, 0.765), (71, 0.63)],
    )
    def test_fatigue_penalty(self, fatigue, expected):
        attacker = _attacker(fatigue=fatigue)
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        probability = AttackLineSystem.calculate_hit_probability(attacker, target)

        assert probability == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("experience", "expected"),
        [(2, 0.99), (3, 1.0)],
    )
    def test_veterancy_bonus(self, experience, expected):
        attacker = _attacker(experience=experience)
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        probability = AttackLineSystem.calculate_hit_probability(attacker, target)

        assert probability == pytest.approx(expected)

    @pytest.mark.parametrize(
        ("move_mode", "expected"),
        [("fast", 0.45), ("sneak", 0.72), ("normal", 0.9)],
    )
    def test_move_mode_penalty(self, move_mode, expected):
        attacker = _attacker(move_mode=move_mode)
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        probability = AttackLineSystem.calculate_hit_probability(attacker, target)

        assert probability == pytest.approx(expected)

    def test_morale_modifier_is_applied(self):
        attacker = _attacker(morale=SimpleNamespace(value=5))
        target = AttackTarget(position=Vec2(0, 0), distance=0)
        modifier = MoraleSystem.get_accuracy_modifier(MoraleSystem.get_state(5))

        probability = AttackLineSystem.calculate_hit_probability(attacker, target)

        assert probability == pytest.approx(0.9 * modifier)

    @pytest.mark.parametrize(
        ("weather", "expected"),
        [("rain", 0.8), ("fog", 0.7), ("snow", 0.75), ("clear", 0.9)],
    )
    def test_weather_penalty(self, weather, expected):
        attacker = _attacker()
        target = AttackTarget(position=Vec2(0, 0), distance=0)
        game_map = SimpleNamespace(weather=weather)

        probability = AttackLineSystem.calculate_hit_probability(attacker, target, game_map)

        assert probability == pytest.approx(expected)

    def test_captured_weapon_penalty(self):
        attacker = _attacker(captured=True)
        target = AttackTarget(position=Vec2(0, 0), distance=0)

        probability = AttackLineSystem.calculate_hit_probability(attacker, target)

        assert probability == pytest.approx(0.72)

    def test_probability_is_clamped_to_zero(self):
        attacker = _attacker()
        target = AttackTarget(position=Vec2(0, 0), distance=0)
        game_map = SimpleNamespace(
            get_tile=lambda tx, ty: SimpleNamespace(cover_level=100, concealment=100)
        )

        assert AttackLineSystem.calculate_hit_probability(attacker, target, game_map) == 0.0


# ===========================================================================
# Status mapping / colors
# ===========================================================================


@pytest.mark.unit
class TestStatusMapping:
    @pytest.mark.parametrize(
        ("probability", "expected"),
        [
            (1.0, AttackLineStatus.HIT_HIGH),
            (0.6, AttackLineStatus.HIT_HIGH),
            (0.59, AttackLineStatus.HIT_MODERATE),
            (0.3, AttackLineStatus.HIT_MODERATE),
            (0.29, AttackLineStatus.HIT_LOW),
            (0.1, AttackLineStatus.HIT_LOW),
            (0.09, AttackLineStatus.HIT_IMPOSSIBLE),
            (0.0, AttackLineStatus.HIT_IMPOSSIBLE),
        ],
    )
    def test_hit_probability_to_status(self, probability, expected):
        assert AttackLineSystem._hit_probability_to_status(probability) is expected

    @pytest.mark.parametrize("status", list(AttackLineStatus))
    def test_every_status_has_a_color(self, status):
        system = AttackLineSystem()
        color = system.get_line_color(status)
        assert isinstance(color, tuple)
        assert len(color) == 4

    def test_unknown_status_uses_out_of_range_color(self):
        system = AttackLineSystem()
        assert system.get_line_color(object()) == system.COLOR_OUT_OF_RANGE


# ===========================================================================
# Removal and fade-out
# ===========================================================================


@pytest.mark.unit
class TestRemoveAndFade:
    def test_remove_unknown_attack_is_noop(self):
        system = AttackLineSystem()
        system.remove_attack("missing")
        assert system._confirmed_attacks == {}
        assert system._fading_lines == []

    def test_remove_without_active_source_starts_no_fade(self):
        system = AttackLineSystem()
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(1, 1))

        system.remove_attack("u1")

        assert system._confirmed_attacks == {}
        assert system._fading_lines == []

    def test_remove_with_active_source_starts_fade(self):
        system = AttackLineSystem()
        system._confirmed_sources["u1"] = Vec2(0, 0)
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(10, 10))

        system.remove_attack("u1")

        assert system._confirmed_attacks == {}
        assert len(system._fading_lines) == 1
        assert system._fading_lines[0]["alpha"] == 200
        assert system._fading_lines[0]["color"] == system.COLOR_CAN_ATTACK[:3]

    def test_update_fading_keeps_and_fades_young_lines(self, monkeypatch):
        system = AttackLineSystem()
        system._fading_lines = [
            {
                "source": Vec2(0, 0),
                "target": Vec2(10, 10),
                "color": (0, 255, 0),
                "alpha": 200,
                "start_tick": 100.0,
            }
        ]
        monkeypatch.setattr(time, "monotonic", lambda: 100.5)

        remaining = system.update_fading()

        assert len(remaining) == 1
        assert remaining[0]["alpha"] == 133
        assert system._fading_lines == remaining

    def test_update_fading_drops_expired_lines(self, monkeypatch):
        system = AttackLineSystem()
        system._fading_lines = [
            {
                "source": Vec2(0, 0),
                "target": Vec2(10, 10),
                "color": (0, 255, 0),
                "alpha": 200,
                "start_tick": 100.0,
            }
        ]
        monkeypatch.setattr(time, "monotonic", lambda: 102.0)

        assert system.update_fading() == []
        assert system._fading_lines == []

    def test_update_fading_without_lines(self):
        assert AttackLineSystem().update_fading() == []

    def test_clear_all(self):
        system = AttackLineSystem()
        system.begin_attack("u1", Vec2(0, 0))
        system._confirmed_attacks["u1"] = AttackTarget(position=Vec2(1, 1))

        system.clear_all()

        assert system._confirmed_attacks == {}
        assert system.state.active is False
