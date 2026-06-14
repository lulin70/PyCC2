"""Tests for Phase C P1+Phase D Core: SquadGroups, CombatLog, StrategicMap, Airdrop."""

import time
from unittest.mock import MagicMock, patch

import pytest

from pycc2.domain.systems.airdrop_supply import (
    AirdropSupplySystem,
    SupplyType,
)
from pycc2.presentation.ui.combat_log import (
    CombatEvent,
    CombatEventType,
    CombatLog,
)
from pycc2.presentation.ui.squad_group_manager import (
    SquadGroupManager,
)
from pycc2.presentation.ui.strategic_map_view import (
    Sector,
    SectorStatus,
    StrategicMapView,
)


@pytest.fixture
def make_unit():
    """Factory to create mock units."""

    def _make_unit(name: str, x: float = 0.0, y: float = 0.0):
        unit = MagicMock()
        unit.name = name
        unit.position_component = MagicMock()
        unit.position_component.x = x
        unit.position_component.y = y
        return unit

    return _make_unit


class TestSquadGroupManager:
    """Test suite for C4 Squad Group Manager (10 tests)."""

    def test_initialization(self):
        """Test manager initializes with 9 empty groups."""
        mgr = SquadGroupManager()

        assert mgr.MAX_GROUPS == 9
        assert len(mgr._groups) == 9
        assert mgr.total_units_in_groups == 0

    def test_create_group_valid(self, make_unit):
        """Test creating a valid group."""
        mgr = SquadGroupManager()
        units = [make_unit("Unit1", 1, 1), make_unit("Unit2", 5, 5)]

        result = mgr.create_group(1, units)

        assert result is True
        assert len(mgr.select_group(1)) == 2

    def test_create_group_invalid_number(self, make_unit):
        """Test creating group with invalid number."""
        mgr = SquadGroupManager()

        assert mgr.create_group(0, []) is False
        assert mgr.create_group(10, []) is False
        assert mgr.create_group(-1, []) is False

    def test_select_group(self, make_unit):
        """Test selecting units from group."""
        mgr = SquadGroupManager()
        units = [make_unit("U1"), make_unit("U2")]
        mgr.create_group(3, units)

        selected = mgr.select_group(3)

        assert len(selected) == 2
        assert selected[0].name == "U1"

    def test_select_empty_group(self):
        """Test selecting empty group returns empty list."""
        mgr = SquadGroupManager()

        assert mgr.select_group(5) == []

    def test_get_group_bounds(self, make_unit):
        """Test getting bounding box for group."""
        mgr = SquadGroupManager()
        units = [
            make_unit("U1", 2, 3),
            make_unit("U2", 8, 9),
            make_unit("U3", 5, 5),
        ]
        mgr.create_group(2, units)

        bounds = mgr.get_group_bounds(2)

        assert bounds == (2, 3, 8, 9)

    def test_get_group_bounds_empty(self):
        """Test bounds of empty group is None."""
        mgr = SquadGroupManager()

        assert mgr.get_group_bounds(7) is None

    def test_clear_group(self, make_unit):
        """Test clearing a specific group."""
        mgr = SquadGroupManager()
        mgr.create_group(1, [make_unit("U1")])

        assert mgr.clear_group(1) is True
        assert mgr.select_group(1) == []

    def test_clear_all_groups(self, make_unit):
        """Test clearing all groups."""
        mgr = SquadGroupManager()
        mgr.create_group(1, [make_unit("U1")])
        mgr.create_group(2, [make_unit("U2")])

        mgr.clear_all_groups()

        assert mgr.total_units_in_groups == 0

    def test_remove_unit_from_all(self, make_unit):
        """Test removing unit from all groups."""
        mgr = SquadGroupManager()
        u1 = make_unit("Shared")
        mgr.create_group(1, [u1, make_unit("Other")])
        mgr.create_group(2, [u1])

        mgr.remove_unit_from_all_groups(u1)

        assert u1 not in mgr.select_group(1)
        assert u1 not in mgr.select_group(2)


class TestCombatLog:
    """Test suite for C5 Combat Event Log (12 tests)."""

    def test_initialization(self):
        """Test log initializes empty."""
        log = CombatLog()

        assert log.event_count == 0
        assert log.MAX_VISIBLE == 8
        assert log.MAX_EVENTS == 100
        assert log.expanded is False

    def test_add_event(self):
        """Test adding event increments count."""
        log = CombatLog()
        event = CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.HIT,
            source_name="Rifle",
            target_name="Enemy",
        )

        log.add_event(event)

        assert log.event_count == 1

    def test_create_event(self):
        """Test creating event via helper method."""
        log = CombatLog()

        event = log.create_event(
            event_type=CombatEventType.KILL,
            source_name="MG",
            target_name="Soldier",
            damage=1,
        )

        assert log.event_count == 1
        assert event.damage == 1
        assert event.event_type == CombatEventType.KILL

    def test_max_events_limit(self):
        """Test that events are capped at MAX_EVENTS."""
        log = CombatLog()
        log.MAX_EVENTS = 5

        for _i in range(10):
            log.create_event(event_type=CombatEventType.ATTACK)

        assert log.event_count == 5

    def test_event_format_short_kill(self):
        """Test short format for kill event."""
        event = CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.KILL,
            source_name="Rifle",
            target_name="Enemy",
            damage=1,
        )

        text = event.format_short()

        assert "KIA" in text
        assert "Rifle" in text

    def test_event_format_full(self):
        """Test full format includes details."""
        event = CombatEvent(
            timestamp=time.time(),
            event_type=CombatEventType.HIT,
            source_name="Shooter",
            target_name="Target",
            damage=25,
            position=(10, 15),
        )

        full = event.format_full()

        assert "HIT" in full
        assert "Damage: 25" in full
        assert "Position: (10, 15)" in full

    def test_get_recent_events(self):
        """Test getting recent events."""
        log = CombatLog()

        for _i in range(10):
            log.create_event(event_type=CombatEventType.MOVEMENT)

        recent = log.get_recent_events(3)

        assert len(recent) == 3

    def test_scroll_functionality(self):
        """Test scroll up/down."""
        log = CombatLog()

        for _i in range(20):
            log.create_event(event_type=CombatEventType.ATTACK)

        initial_offset = log.scroll_offset
        log.scroll_up(5)
        assert log.scroll_offset < initial_offset

        log.scroll_down(3)
        assert log.scroll_offset > 0

    def test_toggle_expanded(self):
        """Test toggling expanded mode."""
        log = CombatLog()

        assert log.expanded is False
        log.toggle_expanded()
        assert log.expanded is True
        log.toggle_expanded()
        assert log.expanded is False

    def test_clear_log(self):
        """Test clearing all events."""
        log = CombatLog()
        log.create_event(event_type=CombatEventType.ATTACK)
        log.create_event(event_type=CombatEventType.HIT)

        log.clear()

        assert log.event_count == 0

    @patch("pygame.font")
    def test_render_minimal(self, mock_font):
        """Test minimal rendering doesn't crash."""
        log = CombatLog()
        log.create_event(
            event_type=CombatEventType.KILL,
            source_name="A",
            target_name="B",
            damage=1,
        )

        surface = MagicMock()
        log.render_minimal(surface, (1000, 500))

    @staticmethod
    def _get_event_color_test():
        """Test event color mapping."""
        colors = {
            CombatEventType.KILL: (255, 80, 80),
            CombatEventType.HIT: (255, 180, 50),
            CombatEventType.MISS: (150, 150, 150),
        }

        for event_type, expected_color in colors.items():
            actual = CombatLog._get_event_color(event_type)
            assert actual == expected_color


class TestStrategicMapView:
    """Test suite for D1 Strategic Map View (10 tests)."""

    def test_initialization(self):
        """Test map initializes with default sectors."""
        view = StrategicMapView()

        assert view.sector_count >= 5
        assert "arnhem" in view.sectors
        assert "nijmegen" in view.sectors

    def test_sector_defaults(self):
        """Test sectors have correct defaults."""
        view = StrategicMapView()

        arnhem = view.get_sector("arnhem")

        assert arnhem is not None
        assert arnhem.name == "Arnhem"
        assert isinstance(arnhem.status, SectorStatus)

    def test_handle_click_on_sector(self):
        """Test clicking on a sector returns sector ID."""
        view = StrategicMapView()

        arnhem_pos = view.sectors["arnhem"].position
        result = view.handle_click((int(arnhem_pos[0]), int(arnhem_pos[1])))

        assert result == "arnhem"

    def test_handle_click_miss(self):
        """Test clicking away from sectors returns None."""
        view = StrategicMapView()

        result = view.handle_click((50, 50))

        assert result is None

    def test_sector_status_colors(self):
        """Test sector colors update with status."""
        sector = Sector(name="Test", position=(100, 100))

        sector.status = SectorStatus.ALLIED_CONTROL
        sector.update_color()
        assert sector.color == (0, 150, 0)

        sector.status = SectorStatus.AXIS_CONTROL
        sector.update_color()
        assert sector.color == (150, 0, 0)

    def test_allied_sectors_property(self):
        """Test getting allied-controlled sectors."""
        view = StrategicMapView()
        view.sectors["eindhoven"].status = SectorStatus.ALLIED_CONTROL
        view.sectors["eindhoven"].update_color()

        allied = view.allied_sectors

        assert "eindhoven" in allied

    @patch("pygame.font")
    def test_render_doesnt_crash(self, mock_font):
        """Test rendering doesn't raise exceptions."""
        view = StrategicMapView()

        surface = MagicMock()
        view.render(surface, (1024, 768))

    def test_get_nonexistent_sector(self):
        """Test getting nonexistent sector returns None."""
        view = StrategicMapView()

        assert view.get_sector("nonexistent") is None

    def test_sector_operations_list(self):
        """Test operations list in sector."""
        sector = Sector(name="Op", position=(0, 0))
        sector.operations.extend(["Op1", "Op2"])

        assert len(sector.operations) == 2


class TestAirdropSupplySystem:
    """Test suite for D2 Airdrop Supply System (10 tests)."""

    def test_initialization(self):
        """Test system initializes empty."""
        system = AirdropSupplySystem()

        assert system.active_supply_count == 0
        assert system.total_drops == 0

    def test_spawn_supply_drop(self):
        """Test spawning supply crate."""
        system = AirdropSupplySystem()

        crate = system.spawn_supply_drop(
            lz_position=(10.0, 20.0),
            supply_type=SupplyType.AMMO,
            quantity=10,
        )

        assert crate.supply_type == SupplyType.AMMO
        assert crate.quantity == 10
        assert crate.position == (10.0, 20.0)
        assert not crate.picked_up
        assert system.active_supply_count == 1

    def test_spawn_random_supply(self):
        """Test spawning without specifying type."""
        system = AirdropSupplySystem()

        crate = system.spawn_supply_drop((5.0, 5.0))

        assert isinstance(crate.supply_type, SupplyType)
        assert 5 <= crate.quantity <= 15

    def test_check_pickup_in_range(self, make_unit):
        """Test pickup detection when in range."""
        system = AirdropSupplySystem()
        system.spawn_supply_drop((10.0, 10.0), SupplyType.AMMO)

        unit = make_unit("Picker", 10.0, 10.0)

        crate = system.check_pickup(unit, pickup_range=1.5)

        assert crate is not None
        assert crate.supply_type == SupplyType.AMMO

    def test_check_pickup_out_of_range(self, make_unit):
        """Test pickup detection when out of range."""
        system = AirdropSupplySystem()
        system.spawn_supply_drop((10.0, 10.0), SupplyType.MEDIKIT)

        unit = make_unit("FarAway", 50.0, 50.0)

        assert system.check_pickup(unit) is None

    def test_apply_ammo_supply(self, make_unit):
        """Test applying ammo supply to unit."""
        system = AirdropSupplySystem()
        crate = system.spawn_supply_drop((0, 0), SupplyType.AMMO, quantity=8)

        unit = make_unit("Soldier")
        unit.weapon_component = MagicMock()
        unit.weapon_component.current_ammo = 2
        unit.weapon_component.max_ammo = 10

        result = system.apply_supply(unit, crate)

        assert result is True
        assert unit.weapon_component.current_ammo == 10  # min(10, 2+8)
        assert crate.picked_up is True

    def test_apply_medkit_supply(self, make_unit):
        """Test applying medkit supply."""
        system = AirdropSupplySystem()
        crate = system.spawn_supply_drop((0, 0), SupplyType.MEDIKIT)

        unit = make_unit("Wounded")
        unit.health_component = MagicMock()
        unit.health_component.current_hp = 40
        unit.health_component.max_hp = 100

        system.apply_supply(unit, crate)

        assert unit.health_component.current_hp == 60  # 40 + 20

    def test_apply_rations_supply(self, make_unit):
        """Test applying rations for morale."""
        system = AirdropSupplySystem()
        crate = system.spawn_supply_drop((0, 0), SupplyType.RATIONS)

        unit = make_unit("Hungry")
        unit.morale_component = MagicMock()
        unit.morale_component.current_morale = 70.0

        system.apply_supply(unit, crate)

        assert unit.morale_component.current_morale == 85.0  # 70 + 15

    def test_double_pickup_prevented(self, make_unit):
        """Test same crate can't be picked twice."""
        system = AirdropSupplySystem()
        system.spawn_supply_drop((0, 0), SupplyType.AMMO)

        unit = make_unit("Greedy")
        unit.weapon_component = MagicMock()
        unit.weapon_component.current_ammo = 5
        unit.weapon_component.max_ammo = 10

        first = system.check_pickup(unit)
        system.apply_supply(unit, first)

        second = system.check_pickup(unit)

        assert second is None

    def test_scenario_supplies_spawning(self):
        """Test spawning multiple supplies for scenario."""
        system = AirdropSupplySystem()

        lzs = [(10.0, 10.0), (20.0, 20.0), (30.0, 30.0)]
        crates = system.spawn_scenario_supplies(lzs, supplies_per_lz=3)

        assert len(crates) == 9
        assert system.active_supply_count == 9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
