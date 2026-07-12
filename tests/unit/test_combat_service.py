"""Unit tests for CombatService.

Covers CombatService orchestration logic: attack execution with angle-based
damage multipliers, suppression fire, melee resolution, engagement checks,
attack-angle calculation, and angle metadata helpers.

Real components (HealthComponent, MoraleComponent, PositionComponent, ShotResult,
CombatResult, AttackAngle, AttackOrder) are used wherever practical; the
ballistic engine and event bus are stubbed/mocked because they are collaborator
boundaries.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pycc2.domain.combat.combat_result import CombatResult
from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.entities.unit import Faction
from pycc2.domain.systems.ballistic import ShotResult
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.services.combat_service import AttackAngle, AttackOrder, CombatService

# ===========================================================================
# Test fakes / helpers
# ===========================================================================


class StubEventBus:
    """Minimal event bus stub recording publish / publish_named calls."""

    def __init__(self) -> None:
        self.published: list = []

    def subscribe(self, *args, **kwargs) -> None:  # pragma: no cover - unused
        pass

    def publish(self, event) -> None:
        self.published.append(event)

    def publish_named(self, name: str, data: dict) -> None:
        self.published.append({"name": name, "data": data})


class FakeWeapon:
    """Minimal weapon stub with the attributes CombatService reads."""

    def __init__(self, ammo_remaining: int = 100, max_range: int = 120) -> None:
        self.ammo_remaining = ammo_remaining
        self.max_range = max_range


class FakeUnit:
    """Lightweight unit stand-in backed by real health/morale/position.

    Exposes exactly the surface area that CombatService touches: unit_id, name,
    faction, facing, position_component (x/y), is_alive, take_damage, morale.
    """

    def __init__(
        self,
        unit_id: str,
        faction: Faction,
        x: int = 0,
        y: int = 0,
        facing: float = 0.0,
        hp: int = 100,
        max_hp: int = 100,
        morale_value: int = 80,
        weapon: FakeWeapon | None = None,
        name: str | None = None,
    ) -> None:
        self.id = unit_id
        self.unit_id = unit_id
        self.name = name or unit_id
        self.faction = faction
        self.facing = facing
        self.position = PositionComponent(TileCoord(x, y))
        self.health = HealthComponent(hp=hp, max_hp=max_hp)
        self.morale = MoraleComponent(value=morale_value)
        self.weapon = weapon if weapon is not None else FakeWeapon()

    @property
    def position_component(self) -> PositionComponent:
        return self.position

    @property
    def is_alive(self) -> bool:
        return self.health.is_alive

    def take_damage(self, amount: int) -> int:
        return self.health.take_damage(amount)


def _make_service(event_bus: StubEventBus | None = None) -> CombatService:
    """Build a CombatService with mocked collaborators."""
    bus = event_bus if event_bus is not None else StubEventBus()
    return CombatService(
        ballistic_engine=Mock(),
        combat_resolver=Mock(),
        morale_calculator=Mock(),
        event_bus=bus,
    )


def _named_events(bus: StubEventBus, name: str) -> list[dict]:
    """Return data payloads for publish_named events matching name."""
    return [e["data"] for e in bus.published if isinstance(e, dict) and e.get("name") == name]


def _typed_events(bus: StubEventBus) -> list[dict]:
    """Return events published via publish() (no 'name' wrapper key)."""
    return [e for e in bus.published if isinstance(e, dict) and "name" not in e]


# ===========================================================================
# Enum / dataclass integrity
# ===========================================================================


@pytest.mark.unit
class TestAttackAngleEnum:
    """AttackAngle enum completeness."""

    def test_has_five_members(self) -> None:
        members = {m.name for m in AttackAngle}
        assert members == {
            "FRONT",
            "FLANK_LEFT",
            "FLANK_RIGHT",
            "REAR",
            "FRONT_FLANK",
        }

    def test_members_are_distinct(self) -> None:
        values = [m.value for m in AttackAngle]
        assert len(values) == len(set(values))


@pytest.mark.unit
class TestAttackOrder:
    """AttackOrder dataclass defaults."""

    def test_default_weapon_slot_is_primary(self) -> None:
        order = AttackOrder(attacker_id="a1", target_id="t1")
        assert order.weapon_slot == "primary"

    def test_explicit_weapon_slot(self) -> None:
        order = AttackOrder(attacker_id="a1", target_id="t1", weapon_slot="secondary")
        assert order.weapon_slot == "secondary"
        assert order.attacker_id == "a1"
        assert order.target_id == "t1"


# ===========================================================================
# Angle metadata helpers
# ===========================================================================


@pytest.mark.unit
class TestGetAngleDamageMultiplier:
    """get_angle_damage_multiplier mapping."""

    @pytest.mark.parametrize(
        "angle, expected",
        [
            (AttackAngle.FRONT, 1.0),
            (AttackAngle.FLANK_LEFT, 1.5),
            (AttackAngle.FLANK_RIGHT, 1.5),
            (AttackAngle.REAR, 2.0),
            (AttackAngle.FRONT_FLANK, 1.25),
        ],
    )
    def test_known_multipliers(self, angle: AttackAngle, expected: float) -> None:
        service = _make_service()
        assert service.get_angle_damage_multiplier(angle) == expected

    def test_unknown_angle_returns_default(self) -> None:
        service = _make_service()
        assert service.get_angle_damage_multiplier(None) == 1.0  # type: ignore[arg-type]


@pytest.mark.unit
class TestGetAngleDescription:
    """get_angle_description mapping."""

    @pytest.mark.parametrize(
        "angle, expected",
        [
            (AttackAngle.FRONT, "Frontal"),
            (AttackAngle.FLANK_LEFT, "Left Flank"),
            (AttackAngle.FLANK_RIGHT, "Right Flank"),
            (AttackAngle.REAR, "Rear"),
            (AttackAngle.FRONT_FLANK, "Front-Flank"),
        ],
    )
    def test_known_descriptions(self, angle: AttackAngle, expected: str) -> None:
        service = _make_service()
        assert service.get_angle_description(angle) == expected

    def test_unknown_angle_returns_unknown(self) -> None:
        service = _make_service()
        assert service.get_angle_description(None) == "Unknown"  # type: ignore[arg-type]


# ===========================================================================
# Distance + attack angle calculation
# ===========================================================================


@pytest.mark.unit
class TestCalculateDistance:
    """_calculate_distance euclidean behavior."""

    def test_zero_distance(self) -> None:
        service = _make_service()
        a = FakeUnit("a", Faction.ALLIES, x=3, y=3)
        b = FakeUnit("b", Faction.AXIS, x=3, y=3)
        assert service._calculate_distance(a, b) == 0.0

    def test_pythagorean_triple(self) -> None:
        service = _make_service()
        a = FakeUnit("a", Faction.ALLIES, x=0, y=0)
        b = FakeUnit("b", Faction.AXIS, x=3, y=4)
        assert service._calculate_distance(a, b) == 5.0

    def test_symmetric(self) -> None:
        service = _make_service()
        a = FakeUnit("a", Faction.ALLIES, x=1, y=2)
        b = FakeUnit("b", Faction.AXIS, x=4, y=6)
        assert service._calculate_distance(a, b) == service._calculate_distance(b, a)


@pytest.mark.unit
class TestCalculateAttackAngle:
    """calculate_attack_angle quadrant + boundary behavior.

    Formula: relative_angle = (deg(atan2(dy, dx)) - target.facing + 360) % 360
      FRONT       if <=45 or >=315
      FLANK_LEFT  if 45 < a <= 135
      REAR        if 135 < a <= 225
      FLANK_RIGHT otherwise (225 < a < 315)
    """

    def test_front_attack_from_east(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES, x=5, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FRONT

    def test_front_boundary_45_degrees(self) -> None:
        service = _make_service()
        # dx=2, dy=2 -> atan2(2,2)=45°, relative=45 -> FRONT (<=45)
        attacker = FakeUnit("a", Faction.ALLIES, x=4, y=6)
        target = FakeUnit("t", Faction.AXIS, x=2, y=4, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FRONT

    def test_front_boundary_315_degrees(self) -> None:
        service = _make_service()
        # dx=2, dy=-2 -> atan2(-2,2)=-45°=315°, relative=315 -> FRONT (>=315)
        attacker = FakeUnit("a", Faction.ALLIES, x=4, y=2)
        target = FakeUnit("t", Faction.AXIS, x=2, y=4, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FRONT

    def test_flank_left_from_south(self) -> None:
        service = _make_service()
        # dx=0, dy=2 -> atan2(2,0)=90° -> FLANK_LEFT
        attacker = FakeUnit("a", Faction.ALLIES, x=3, y=7)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FLANK_LEFT

    def test_flank_left_boundary_135_degrees(self) -> None:
        service = _make_service()
        # dx=-2, dy=2 -> atan2(2,-2)=135° -> FLANK_LEFT (<=135)
        attacker = FakeUnit("a", Faction.ALLIES, x=2, y=6)
        target = FakeUnit("t", Faction.AXIS, x=4, y=4, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FLANK_LEFT

    def test_rear_from_west(self) -> None:
        service = _make_service()
        # dx=-2, dy=0 -> atan2(0,-2)=180° -> REAR
        attacker = FakeUnit("a", Faction.ALLIES, x=1, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.REAR

    def test_rear_boundary_225_degrees(self) -> None:
        service = _make_service()
        # dx=-2, dy=-2 -> atan2(-2,-2)=-135°=225° -> REAR (<=225)
        attacker = FakeUnit("a", Faction.ALLIES, x=2, y=2)
        target = FakeUnit("t", Faction.AXIS, x=4, y=4, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.REAR

    def test_flank_right_from_north(self) -> None:
        service = _make_service()
        # dx=0, dy=-2 -> atan2(-2,0)=-90°=270° -> FLANK_RIGHT
        attacker = FakeUnit("a", Faction.ALLIES, x=3, y=3)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0)
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FLANK_RIGHT

    def test_facing_offsets_relative_angle(self) -> None:
        """Attacker due east of target, but target faces east (90°) -> REAR."""
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES, x=5, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=90.0)
        # bearing=0, relative=(0-90+360)%360=270 -> FLANK_RIGHT
        assert service.calculate_attack_angle(attacker, target) is AttackAngle.FLANK_RIGHT


# ===========================================================================
# can_engage
# ===========================================================================


@pytest.mark.unit
class TestCanEngage:
    """can_engage guard conditions."""

    def test_attacker_eliminated(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES, hp=0, max_hp=100)
        target = FakeUnit("t", Faction.AXIS)
        ok, reason = service.can_engage(attacker, target)
        assert ok is False
        assert reason == "Attacker is eliminated"

    def test_target_already_eliminated(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES)
        target = FakeUnit("t", Faction.AXIS, hp=0, max_hp=100)
        ok, reason = service.can_engage(attacker, target)
        assert ok is False
        assert reason == "Target is already eliminated"

    def test_no_ammunition(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES, weapon=FakeWeapon(ammo_remaining=0))
        target = FakeUnit("t", Faction.AXIS)
        ok, reason = service.can_engage(attacker, target)
        assert ok is False
        assert reason == "No ammunition"

    def test_friendly_faction_blocked(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES)
        target = FakeUnit("t", Faction.ALLIES)
        ok, reason = service.can_engage(attacker, target)
        assert ok is False
        assert reason == "Cannot engage friendly units"

    def test_out_of_range(self) -> None:
        service = _make_service()
        # max_range=120 -> weapon_range=12.0; distance 13 > 12
        attacker = FakeUnit("a", Faction.ALLIES, x=0, y=0, weapon=FakeWeapon(max_range=120))
        target = FakeUnit("t", Faction.AXIS, x=13, y=0)
        ok, reason = service.can_engage(attacker, target)
        assert ok is False
        assert reason.startswith("Target out of range")
        assert "13.0" in reason
        assert "12.0" in reason

    def test_in_range_can_engage(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES, x=0, y=0, weapon=FakeWeapon(max_range=120))
        target = FakeUnit("t", Faction.AXIS, x=10, y=0)
        ok, reason = service.can_engage(attacker, target)
        assert ok is True
        assert reason == "Can engage"

    def test_default_max_range_when_attribute_missing(self) -> None:
        """getattr fallback to 120 when weapon lacks max_range."""
        service = _make_service()
        weapon = SimpleNamespace(ammo_remaining=100)  # no max_range attr
        attacker = FakeUnit("a", Faction.ALLIES, x=0, y=0, weapon=weapon)  # type: ignore[arg-type]
        target = FakeUnit("t", Faction.AXIS, x=5, y=0)
        ok, reason = service.can_engage(attacker, target)
        assert ok is True
        assert reason == "Can engage"


# ===========================================================================
# execute_attack
# ===========================================================================


@pytest.mark.unit
class TestExecuteAttack:
    """execute_attack hit / miss / angle / kill paths."""

    def test_miss_returns_no_hit_result(self) -> None:
        bus = StubEventBus()
        service = _make_service(bus)
        miss = ShotResult(hit=False, damage_dealt=0.0, distance=2.0, reason="miss")
        service.ballistic_engine.calculate_shot.return_value = miss

        attacker = FakeUnit("a", Faction.ALLIES, x=5, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0, hp=100, morale_value=80)

        result = service.execute_attack(attacker, target)

        assert isinstance(result, CombatResult)
        assert result.shots_fired == 1
        assert result.shots_hit == 0
        assert result.total_damage == 0
        assert result.target_eliminated is False
        assert result.shot_results == [miss]
        # No damage applied, no events published
        assert target.health.hp == 100
        assert target.morale.value == 80
        assert bus.published == []

    def test_hit_front_applies_damage_and_morale(self) -> None:
        bus = StubEventBus()
        service = _make_service(bus)
        shot = ShotResult(hit=True, damage_dealt=20.0, distance=2.0, reason="hit")
        service.ballistic_engine.calculate_shot.return_value = shot

        attacker = FakeUnit("a", Faction.ALLIES, x=5, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0, hp=100, morale_value=80)

        result = service.execute_attack(attacker, target)

        # FRONT -> multiplier 1.0 -> no adjustment -> take_damage(20)
        assert result.shots_hit == 1
        assert result.total_damage == 20.0
        assert result.target_eliminated is False
        assert target.health.hp == 80
        # morale_impact = -max(1, 20//5) = -4
        assert target.morale.value == 76
        # UnitAttacked published, no UnitKilled
        attacked = _named_events(bus, "UnitAttacked")
        assert len(attacked) == 1
        assert attacked[0]["attacker_id"] == "a"
        assert attacked[0]["target_id"] == "t"
        assert attacked[0]["is_hit"] is True
        assert attacked[0]["damage"] == 20.0
        assert _typed_events(bus) == []
        # ballistic called with default weapon_slot
        service.ballistic_engine.calculate_shot.assert_called_once_with(attacker, target, "primary")

    def test_hit_flank_left_applies_1_5x_damage(self) -> None:
        bus = StubEventBus()
        service = _make_service(bus)
        shot = ShotResult(hit=True, damage_dealt=20.0, distance=2.0, reason="hit")
        service.ballistic_engine.calculate_shot.return_value = shot

        # attacker south of target -> FLANK_LEFT (mult 1.5)
        attacker = FakeUnit("a", Faction.ALLIES, x=3, y=7)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0, hp=100, morale_value=80)

        result = service.execute_attack(attacker, target)

        # adjusted = 20 * 1.5 = 30 -> take_damage(30)
        assert result.total_damage == 30.0
        assert result.shot_results[0].damage_dealt == 30.0
        assert target.health.hp == 70
        # morale_impact = -max(1, 30//5) = -6 (no REAR bonus)
        assert target.morale.value == 74
        assert result.target_eliminated is False

    def test_hit_rear_applies_2x_damage_and_1_5x_morale(self) -> None:
        bus = StubEventBus()
        service = _make_service(bus)
        shot = ShotResult(hit=True, damage_dealt=20.0, distance=2.0, reason="hit")
        service.ballistic_engine.calculate_shot.return_value = shot

        # attacker west of target -> REAR (mult 2.0)
        attacker = FakeUnit("a", Faction.ALLIES, x=1, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0, hp=100, morale_value=80)

        result = service.execute_attack(attacker, target)

        # adjusted = 20 * 2.0 = 40 -> take_damage(40)
        assert result.total_damage == 40.0
        assert result.shot_results[0].damage_dealt == 40.0
        assert target.health.hp == 60
        # morale_impact = -max(1, 40//5) = -8; REAR -> int(-8 * 1.5) = -12
        assert target.morale.value == 68
        assert _named_events(bus, "UnitAttacked")[0]["damage"] == 40.0

    def test_hit_kills_target_publishes_unit_killed(self) -> None:
        bus = StubEventBus()
        service = _make_service(bus)
        shot = ShotResult(hit=True, damage_dealt=50.0, distance=2.0, reason="hit")
        service.ballistic_engine.calculate_shot.return_value = shot

        attacker = FakeUnit("a", Faction.ALLIES, x=5, y=5)
        target = FakeUnit(
            "t", Faction.AXIS, x=3, y=5, facing=0.0, hp=10, max_hp=100, morale_value=80
        )

        result = service.execute_attack(attacker, target)

        # FRONT mult 1.0; take_damage(50) -> actual 10 (clamped), target dies
        assert result.total_damage == 10.0
        assert result.target_eliminated is True
        assert target.is_alive is False
        assert target.health.hp == 0
        # Both UnitAttacked and UnitKilled published
        attacked = _named_events(bus, "UnitAttacked")
        assert len(attacked) == 1
        assert attacked[0]["damage"] == 10.0
        killed = _typed_events(bus)
        assert len(killed) == 1
        assert killed[0]["unit_id"] == "t"
        assert killed[0]["killer_id"] == "a"
        assert killed[0]["position"] == (3, 5)
        assert killed[0]["faction"] == "AXIS"

    def test_weapon_slot_passed_through(self) -> None:
        bus = StubEventBus()
        service = _make_service(bus)
        shot = ShotResult(hit=True, damage_dealt=20.0, distance=2.0, reason="hit")
        service.ballistic_engine.calculate_shot.return_value = shot

        attacker = FakeUnit("a", Faction.ALLIES, x=5, y=5)
        target = FakeUnit("t", Faction.AXIS, x=3, y=5, facing=0.0)

        service.execute_attack(attacker, target, weapon_slot="secondary")

        service.ballistic_engine.calculate_shot.assert_called_once_with(
            attacker, target, "secondary"
        )


# ===========================================================================
# execute_suppression_fire
# ===========================================================================


@pytest.mark.unit
class TestExecuteSuppressionFire:
    """execute_suppression_fire burst behavior."""

    def test_default_burst_size_returns_three_results(self) -> None:
        service = _make_service()
        shots = [
            ShotResult(hit=False, distance=5.0, reason="suppression"),
            ShotResult(hit=True, damage_dealt=5.0, distance=5.0, reason="suppression"),
            ShotResult(hit=False, distance=5.0, reason="suppression"),
        ]
        service.ballistic_engine.calculate_suppression_shot.side_effect = shots

        attacker = FakeUnit("a", Faction.ALLIES)
        results = service.execute_suppression_fire(attacker, (10, 10))

        assert len(results) == 3
        assert results == shots
        assert service.ballistic_engine.calculate_suppression_shot.call_count == 3
        service.ballistic_engine.calculate_suppression_shot.assert_called_with(attacker, (10, 10))

    def test_custom_burst_size(self) -> None:
        service = _make_service()
        service.ballistic_engine.calculate_suppression_shot.return_value = ShotResult(
            hit=False, distance=1.0
        )

        attacker = FakeUnit("a", Faction.ALLIES)
        results = service.execute_suppression_fire(attacker, (1, 1), burst_size=5)

        assert len(results) == 5
        assert service.ballistic_engine.calculate_suppression_shot.call_count == 5

    def test_zero_burst_returns_empty(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES)
        results = service.execute_suppression_fire(attacker, (1, 1), burst_size=0)
        assert results == []
        assert service.ballistic_engine.calculate_suppression_shot.call_count == 0


# ===========================================================================
# resolve_melee_combat
# ===========================================================================


@pytest.mark.unit
class TestResolveMeleeCombat:
    """resolve_melee_combat fixed base damage."""

    def test_applies_base_damage_15(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES)
        defender = FakeUnit("d", Faction.AXIS, hp=100, morale_value=80)

        result = service.resolve_melee_combat(attacker, defender)

        assert isinstance(result, CombatResult)
        assert result.shots_fired == 0
        assert result.shots_hit == 1
        assert result.total_damage == 15.0
        assert result.target_eliminated is False
        assert defender.health.hp == 85

    def test_melee_kills_low_hp_defender(self) -> None:
        service = _make_service()
        attacker = FakeUnit("a", Faction.ALLIES)
        defender = FakeUnit("d", Faction.AXIS, hp=10, max_hp=100)

        result = service.resolve_melee_combat(attacker, defender)

        assert result.total_damage == 10.0
        assert result.target_eliminated is True
        assert defender.is_alive is False
        assert defender.health.hp == 0
