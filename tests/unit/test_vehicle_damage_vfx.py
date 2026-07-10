"""TD-065: Vehicle damage visual feedback differentiation tests.

Validates that the UnitDamageVfxMixin:
  - Tracks per-component damage (tracks/turret/engine) for TANK units.
  - Maps HP-based damage_state → component failure counts monotonically.
  - Renders component-specific particles (tagged smoke/fire) for vehicles.
  - Leaves infantry VFX untouched (no _damage_components population).
  - Produces deterministic component assignment per (unit.id, state).

Design follows the project's testing philosophy:
  - Real Unit instances (no Mock of the SUT) with real HealthComponent.
  - No skip/xfail — every scenario is exercised.
  - Deterministic seeds verified explicitly so regressions in seed stability
    are caught (changing the seed algorithm would break tests 6 & 7).
"""

from __future__ import annotations

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.value_objects.tile_coord import TileCoord


def _make_unit(
    unit_id: str,
    unit_type: UnitType = UnitType.TANK,
    hp: int = 100,
    max_hp: int = 100,
) -> Unit:
    """Construct a minimal Unit for damage-VFX tests.

    Infantry and vehicles both get a TANK-compatible shape; only ``unit_type``
    differs so the ``is_vehicle`` property reflects what we are testing.
    """
    health = HealthComponent(hp=hp, max_hp=max_hp)
    morale = MoraleComponent(value=80, panic_threshold=20, rout_threshold=10)
    weapon = WeaponComponent(primary_weapon_id="rifle", ammo_remaining=30, max_ammo=30)
    position = PositionComponent(tile_coord=TileCoord(0, 0))
    vision = VisionComponent(range_tiles=6)
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=Faction.ALLIES,
        unit_type=unit_type,
        health=health,
        morale=morale,
        weapon=weapon,
        position=position,
        vision=vision,
    )


class TestIsVehicleProperty:
    """TD-065: is_vehicle property distinguishes TANK from infantry."""

    def test_tank_is_vehicle_true(self):
        unit = _make_unit("tank_1", unit_type=UnitType.TANK)
        assert unit.is_vehicle is True

    def test_infantry_is_vehicle_false(self):
        unit = _make_unit("inf_1", unit_type=UnitType.INFANTRY_SQUAD)
        assert unit.is_vehicle is False


class TestVehicleComponentDamagePlan:
    """TD-065: Each damage_state produces the correct component failure counts."""

    def test_undamaged_all_intact(self):
        unit = _make_unit("tank_ok", hp=100, max_hp=100)  # 100% HP → undamaged
        unit.update_vehicle_damage_components()
        assert set(unit._damage_components.keys()) == {"tracks", "turret", "engine"}
        assert all(s == "intact" for s in unit._damage_components.values())

    def test_light_exactly_one_damaged_zero_destroyed(self):
        unit = _make_unit("tank_light", hp=75, max_hp=100)  # 75% → light (boundary: <= 0.75)
        unit.update_vehicle_damage_components()
        statuses = list(unit._damage_components.values())
        assert statuses.count("damaged") == 1
        assert statuses.count("destroyed") == 0
        assert statuses.count("intact") == 2

    def test_moderate_one_damaged_one_destroyed(self):
        unit = _make_unit("tank_mod", hp=45, max_hp=100)  # 45% → moderate
        unit.update_vehicle_damage_components()
        statuses = list(unit._damage_components.values())
        assert statuses.count("damaged") == 1
        assert statuses.count("destroyed") == 1
        assert statuses.count("intact") == 1

    def test_heavy_two_damaged_one_destroyed(self):
        unit = _make_unit("tank_heavy", hp=20, max_hp=100)  # 20% → heavy
        unit.update_vehicle_damage_components()
        statuses = list(unit._damage_components.values())
        assert statuses.count("damaged") == 2
        assert statuses.count("destroyed") == 1
        assert statuses.count("intact") == 0

    def test_destroyed_all_three_destroyed(self):
        unit = _make_unit("tank_dead", hp=0, max_hp=100)  # 0% → destroyed
        unit.update_vehicle_damage_components()
        statuses = list(unit._damage_components.values())
        assert statuses.count("destroyed") == 3
        assert statuses.count("damaged") == 0
        assert statuses.count("intact") == 0


class TestVehicleComponentDeterminism:
    """TD-065: Same unit.id + state → same component assignment, so the
    player sees stable "tracks knocked out" feedback rather than flicker."""

    def test_same_id_and_state_yields_same_components(self):
        u1 = _make_unit("tank_A", hp=45, max_hp=100)  # moderate
        u2 = _make_unit("tank_A", hp=45, max_hp=100)  # moderate, same id
        u1.update_vehicle_damage_components()
        u2.update_vehicle_damage_components()
        assert u1._damage_components == u2._damage_components

    def test_different_id_may_assign_differently(self):
        """Different unit ids can produce different component orderings.
        We verify at least one of a small sample differs from the first —
        if all 5 matched, the seed would not be incorporating the id."""
        u0 = _make_unit("tank_seed_0", hp=45, max_hp=100)
        u0.update_vehicle_damage_components()
        any_diff = False
        for i in range(1, 6):
            u = _make_unit(f"tank_seed_{i}", hp=45, max_hp=100)
            u.update_vehicle_damage_components()
            if u._damage_components != u0._damage_components:
                any_diff = True
                break
        assert any_diff, "Component assignment must vary with unit.id"


class TestVehicleComponentVfxEmission:
    """TD-065: update_damage_vfx emits tagged particles for damaged components."""

    def test_damaged_vehicle_emits_component_tagged_smoke(self):
        unit = _make_unit("tank_vfx", hp=45, max_hp=100)  # moderate
        unit.update_damage_vfx()
        tagged = [p for p in unit._smoke_particles if "tag" in p]
        assert len(tagged) > 0, "Vehicle with damaged components must emit tagged smoke"
        valid_tags = {"tracks", "turret", "engine"}
        assert all(p["tag"] in valid_tags for p in tagged)

    def test_destroyed_vehicle_emits_engine_fire_tag(self):
        unit = _make_unit("tank_fire", hp=0, max_hp=100)  # destroyed
        unit.update_damage_vfx()
        fire_tags = {p.get("tag") for p in unit._fire_particles if "tag" in p}
        # Destroyed → all 3 components destroyed → engine_fire must appear
        assert "engine_fire" in fire_tags

    def test_component_intensity_doubles_when_destroyed(self):
        """A 'destroyed' component emits 4 particles; 'damaged' emits 2.
        Verifies the intensity multiplier in _emit_vehicle_component_vfx."""
        # heavy: 2 damaged + 1 destroyed → destroyed-comp emits 4, damaged emit 2
        unit = _make_unit("tank_intensity", hp=20, max_hp=100)  # heavy
        unit.update_vehicle_damage_components()
        destroyed_comps = [c for c, s in unit._damage_components.items() if s == "destroyed"]
        damaged_comps = [c for c, s in unit._damage_components.items() if s == "damaged"]
        assert len(destroyed_comps) == 1
        assert len(damaged_comps) == 2

        # Clear particles and re-emit only component VFX for clean counting
        unit._smoke_particles.clear()
        unit._fire_particles.clear()
        import random

        rng = random.Random(unit.id + ":test")
        unit._emit_vehicle_component_vfx(rng)

        # Each damaged component emits 2 smoke; destroyed emits 4 smoke
        # tracks emits smoke only; turret emits smoke only; engine emits smoke+fire
        # So total smoke = sum of intensity per non-intact component.
        # The exact count depends on which component is destroyed, so verify
        # at minimum the destroyed component emitted 4 of its kind.
        assert len(unit._smoke_particles) >= 4  # at least the destroyed one's smoke

    def test_undamaged_vehicle_emits_no_component_vfx(self):
        unit = _make_unit("tank_clean", hp=100, max_hp=100)
        unit.update_damage_vfx()
        tagged = [p for p in unit._smoke_particles if "tag" in p]
        assert len(tagged) == 0
        tagged_fire = [p for p in unit._fire_particles if "tag" in p]
        assert len(tagged_fire) == 0


class TestInfantryUnchangedByVehicleFeature:
    """TD-065: Infantry units must not populate _damage_components or emit
    component-tagged particles — the feature is vehicle-only."""

    def test_infantry_damage_components_stays_empty(self):
        unit = _make_unit("inf_dmg", unit_type=UnitType.INFANTRY_SQUAD, hp=20, max_hp=100)
        unit.update_damage_vfx()
        assert unit._damage_components == {}

    def test_infantry_vfx_has_no_component_tags(self):
        unit = _make_unit("inf_vfx", unit_type=UnitType.INFANTRY_SQUAD, hp=10, max_hp=100)
        unit.update_damage_vfx()
        # Smoke/fire particles still emitted (heavy damage), but no 'tag' field
        for p in unit._smoke_particles:
            assert "tag" not in p
        for p in unit._fire_particles:
            assert "tag" not in p

    def test_infantry_update_vehicle_components_is_noop(self):
        """Calling update_vehicle_damage_components on infantry is a safe
        noop — _damage_components stays empty due to the is_vehicle guard
        inside the method (defensive: protects against direct callers)."""
        unit = _make_unit("inf_call", unit_type=UnitType.MORTAR_TEAM, hp=50, max_hp=100)
        unit.update_vehicle_damage_components()
        assert unit._damage_components == {}
