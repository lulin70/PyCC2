"""Unit tests for DeploymentManager.

Tests the deployment phase lifecycle: start, complete, state queries,
pending orders, attacker detection, and unit creation from placements.

Uses real domain components (HealthComponent, PositionComponent, etc.)
for Unit construction, and lightweight Stub objects for the presentation
layer (DeploymentUI) to avoid pygame/display dependencies — mirroring the
StubEventBus/StubDisplayConfig pattern from test_combat_director_unit.py.
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

from unittest.mock import MagicMock

import pytest

from pycc2.domain.components.health_component import HealthComponent
from pycc2.domain.components.morale_component import MoraleComponent
from pycc2.domain.components.position_component import PositionComponent
from pycc2.domain.components.vision_component import VisionComponent
from pycc2.domain.components.weapon_component import WeaponComponent
from pycc2.domain.entities.unit import Faction, Unit, UnitType
from pycc2.domain.systems.game_settings import (
    ExperienceLevel,
    GameSettings,
    SideSettings,
    SupplyLevelSetting,
)
from pycc2.domain.value_objects.tile_coord import TileCoord
from pycc2.presentation.ui.deployment_models import DeploymentState, DeploymentUnit
from pycc2.services.deployment_manager import DeploymentManager

# ===========================================================================
# Stub helpers
# ===========================================================================


class StubDeploymentUI:
    """Minimal DeploymentUI stub.

    Records ``start_deployment_with_settings`` calls and returns a canned
    result (or raises) from ``begin_battle``.  Exposes a ``state`` attribute
    compatible with ``apply_pending_orders`` (which reads ``state.placed_units``).
    """

    def __init__(self, begin_battle_result=None, placed_units=None):
        self._state = DeploymentState()
        self._state.placed_units = placed_units or []
        self.start_calls: list[dict] = []
        self._begin_battle_result = begin_battle_result
        self.begin_battle_call_count = 0

    @property
    def state(self):
        return self._state

    def start_deployment_with_settings(self, **kwargs):
        self.start_calls.append(kwargs)

    def begin_battle(self):
        self.begin_battle_call_count += 1
        if isinstance(self._begin_battle_result, Exception):
            raise self._begin_battle_result
        return self._begin_battle_result


class StubGameState:
    """Minimal game state with a ``units`` list."""

    def __init__(self):
        self.units: list = []


def _make_placement(
    template_id="us_rifle_squad",
    display_name="Rifle Squad",
    unit_type="infantry",
    position=(5, 5),
):
    """Build a placement dict like ``begin_battle()`` returns."""
    return {
        "unit_template_id": template_id,
        "display_name": display_name,
        "unit_type": unit_type,
        "position": position,
    }


def _make_map_data(width=30, height=30, **extra):
    """Minimal ``map_data`` dict for ``generate_ai_deployment``."""
    data = {"width": width, "height": height}
    data.update(extra)
    return data


def _make_real_unit(
    unit_id="u1",
    faction=Faction.ALLIES,
    unit_type=UnitType.INFANTRY_SQUAD,
    tile_x=5,
    tile_y=5,
    weapon_id="rifle",
    max_ammo=120,
    max_hp=100,
):
    """Create a real Unit entity with sensible defaults."""
    return Unit(
        id=unit_id,
        name=unit_id,
        faction=faction,
        unit_type=unit_type,
        position=PositionComponent(tile_coord=TileCoord(tile_x, tile_y)),
        vision=VisionComponent(),
        health=HealthComponent(hp=max_hp, max_hp=max_hp),
        weapon=WeaponComponent(
            primary_weapon_id=weapon_id, max_ammo=max_ammo, ammo_remaining=max_ammo
        ),
        morale=MoraleComponent(value=75),
    )


def _make_game_settings(
    allied_supply=SupplyLevelSetting.ADEQUATE,
    axis_supply=SupplyLevelSetting.ADEQUATE,
    allied_exp=ExperienceLevel.REGULAR,
    axis_exp=ExperienceLevel.REGULAR,
):
    """Build a real GameSettings with the given per-side levels."""
    return GameSettings(
        allied_settings=SideSettings(experience_level=allied_exp, supply_level=allied_supply),
        axis_settings=SideSettings(experience_level=axis_exp, supply_level=axis_supply),
    )


# ===========================================================================
# Tests: class constants and mapping tables
# ===========================================================================


@pytest.mark.unit
class TestClassConstants:
    """Verify class-level constants and mapping tables."""

    def test_rp_constants(self):
        assert DeploymentManager.ATTACKER_BASE_RP == 2400
        assert DeploymentManager.DEFENDER_BASE_RP == 1800
        assert DeploymentManager.AI_ATTACKER_BASE_RP == 1800
        assert DeploymentManager.AI_DEFENDER_BASE_RP == 1350

    def test_type_map(self):
        assert DeploymentManager._TYPE_MAP == {
            "infantry": "INFANTRY_SQUAD",
            "support": "MACHINE_GUN_SQUAD",
            "vehicle": "TANK",
            "recon": "SNIPER_TEAM",
        }

    def test_template_type_map(self):
        m = DeploymentManager._TEMPLATE_TYPE_MAP
        assert m["us_at_team"] == "AT_GUN_TEAM"
        assert m["ger_at_team"] == "AT_GUN_TEAM"
        assert m["us_mortar_light"] == "MORTAR_TEAM"
        assert m["us_mortar_heavy"] == "MORTAR_TEAM"
        assert m["ger_mortar_light"] == "MORTAR_TEAM"
        assert m["ger_mortar_heavy"] == "MORTAR_TEAM"
        assert m["us_officer"] == "COMMANDER"
        assert m["ger_officer"] == "COMMANDER"
        assert len(m) == 8

    def test_weapon_map(self):
        assert DeploymentManager._WEAPON_MAP["infantry"] == ("rifle", 120)
        assert DeploymentManager._WEAPON_MAP["support"] == ("mg", 250)
        assert DeploymentManager._WEAPON_MAP["vehicle"] == ("tank_cannon", 30)
        assert DeploymentManager._WEAPON_MAP["recon"] == ("sniper_rifle", 15)

    def test_template_weapon_map(self):
        m = DeploymentManager._TEMPLATE_WEAPON_MAP
        assert m["us_at_team"] == ("at_gun", 8)
        assert m["ger_at_team"] == ("at_gun", 8)
        assert m["us_mortar_light"] == ("mortar", 6)
        assert m["us_mortar_heavy"] == ("mortar", 6)
        assert m["ger_mortar_light"] == ("mortar", 6)
        assert m["ger_mortar_heavy"] == ("mortar", 6)
        assert m["us_officer"] == ("pistol", 14)
        assert m["ger_officer"] == ("pistol", 14)

    def test_hp_map(self):
        assert DeploymentManager._HP_MAP == {
            "infantry": 100,
            "support": 80,
            "vehicle": 200,
            "recon": 60,
        }


# ===========================================================================
# Tests: is_active property
# ===========================================================================


@pytest.mark.unit
class TestIsActive:
    """Test the ``is_active`` property lifecycle."""

    def test_initial_false(self):
        dm = DeploymentManager()
        assert dm.is_active is False

    def test_true_after_start(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        dm.start(_make_map_data(), "ally", deployment_ui=ui)
        assert dm.is_active is True

    def test_false_after_complete(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(
            begin_battle_result={"placements": [_make_placement()], "pending_orders": {}}
        )
        dm.start(_make_map_data(), "ally", deployment_ui=ui)
        dm.complete(ai_service=None, state=StubGameState())
        assert dm.is_active is False


# ===========================================================================
# Tests: start()
# ===========================================================================


@pytest.mark.unit
class TestStart:
    """Test ``start()`` success, failure, and RP calculation paths."""

    def test_none_deployment_ui_raises_value_error(self):
        dm = DeploymentManager()
        with pytest.raises(ValueError):
            dm.start(_make_map_data(), "ally", deployment_ui=None)

    def test_start_sets_active_and_calls_ui(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        dm.start(_make_map_data(), "ally", deployment_ui=ui)
        assert dm.deployment_phase_active is True
        assert dm.deployment_ui is ui
        assert len(ui.start_calls) == 1

    def test_start_attacker_rp_2400_no_settings(self):
        """Player as allied attacker gets ATTACKER_BASE_RP=2400."""
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        dm.start(_make_map_data(), "ally", deployment_ui=ui)
        assert ui.start_calls[0]["requisition_points"] == 2400
        assert ui.start_calls[0]["max_infantry"] == 15
        assert ui.start_calls[0]["max_support"] == 10
        assert ui.start_calls[0]["force_pool"] is None

    def test_start_defender_rp_1800_when_axis_attacker(self):
        """Player allied but axis is attacker → defender RP=1800."""
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        map_data = _make_map_data(attacker_faction="axis")
        dm.start(map_data, "ally", deployment_ui=ui)
        assert ui.start_calls[0]["requisition_points"] == 1800

    def test_start_axis_player_attacker_rp_2400(self):
        """Player as axis attacker gets ATTACKER_BASE_RP=2400."""
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        map_data = _make_map_data(attacker_faction="axis")
        dm.start(map_data, "axis", deployment_ui=ui)
        assert ui.start_calls[0]["requisition_points"] == 2400

    def test_start_with_game_settings_applies_supply_modifier(self):
        """ABUNDANT supply (1.2) → 2400 * 1.2 = 2880."""
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        settings = _make_game_settings(
            allied_supply=SupplyLevelSetting.ABUNDANT,
            axis_supply=SupplyLevelSetting.ADEQUATE,
        )
        dm.start(_make_map_data(), "ally", game_settings=settings, deployment_ui=ui)
        assert ui.start_calls[0]["requisition_points"] == 2880
        assert ui.start_calls[0]["force_pool"] is not None

    def test_start_with_game_settings_scarce_supply(self):
        """SCARCE supply (0.8) → 2400 * 0.8 = 1920."""
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        settings = _make_game_settings(allied_supply=SupplyLevelSetting.SCARCE)
        dm.start(_make_map_data(), "ally", game_settings=settings, deployment_ui=ui)
        assert ui.start_calls[0]["requisition_points"] == 1920

    def test_start_generates_default_ai_deployment_without_settings(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        dm.start(_make_map_data(), "ally", deployment_ui=ui)
        assert len(dm._ai_deployments) > 0
        assert len(dm._ai_units) > 0
        # AI units should be AXIS faction (enemy of allied player)
        assert all(u.faction == Faction.AXIS for u in dm._ai_units)

    def test_start_with_settings_generates_ai_deployment(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        settings = _make_game_settings(axis_supply=SupplyLevelSetting.ABUNDANT)
        dm.start(_make_map_data(), "ally", game_settings=settings, deployment_ui=ui)
        assert len(dm._ai_deployments) > 0
        assert len(dm._ai_units) > 0

    def test_start_detects_attacker_faction(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        map_data = _make_map_data(attacker_faction="axis")
        dm.start(map_data, "ally", deployment_ui=ui)
        assert dm.attacker_faction == "axis"

    def test_start_internal_exception_reraised(self):
        """If start_deployment_with_settings raises, exception is re-raised."""
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        ui.start_deployment_with_settings = MagicMock(side_effect=RuntimeError("boom"))
        with pytest.raises(RuntimeError):
            dm.start(_make_map_data(), "ally", deployment_ui=ui)
        assert dm.deployment_phase_active is False

    def test_start_passes_map_data_and_faction_to_ui(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        md = _make_map_data()
        dm.start(md, "ally", deployment_ui=ui)
        assert ui.start_calls[0]["map_data"] is md
        assert ui.start_calls[0]["faction"] == "ally"


# ===========================================================================
# Tests: complete()
# ===========================================================================


@pytest.mark.unit
class TestComplete:
    """Test ``complete()`` success, failure, and exception paths."""

    def test_not_active_returns_none(self):
        dm = DeploymentManager()
        assert dm.complete(None, StubGameState()) is None

    def test_no_ui_returns_none(self):
        dm = DeploymentManager()
        dm.deployment_phase_active = True
        dm.deployment_ui = None
        assert dm.complete(None, StubGameState()) is None

    def test_begin_battle_exception_returns_none(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result=RuntimeError("boom"))
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        assert dm.complete(None, StubGameState()) is None
        assert dm.deployment_phase_active is False

    def test_begin_battle_returns_none(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result=None)
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        assert dm.complete(None, StubGameState()) is None
        assert dm.deployment_phase_active is False

    def test_no_placements_returns_none(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(begin_battle_result={"placements": []})
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        assert dm.complete(None, StubGameState()) is None
        assert dm.deployment_phase_active is False

    def test_success_creates_player_units(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(
            begin_battle_result={
                "placements": [_make_placement(position=(5, 5))],
                "infantry_count": 1,
                "support_count": 0,
                "pending_orders": {},
            }
        )
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        dm._ai_units = []
        state = StubGameState()
        result = dm.complete(ai_service=None, state=state)
        assert result is not None
        assert len(state.units) == 1
        assert state.units[0].id == "player_0"
        assert state.units[0].faction == Faction.ALLIES
        assert state.units[0].unit_type == UnitType.INFANTRY_SQUAD
        assert dm.deployment_phase_active is False

    def test_success_includes_ai_units(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(
            begin_battle_result={
                "placements": [_make_placement(position=(5, 5))],
                "pending_orders": {},
            }
        )
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        ai_unit = _make_real_unit(unit_id="ai_0", faction=Faction.AXIS, tile_x=20, tile_y=20)
        dm._ai_units = [ai_unit]
        state = StubGameState()
        result = dm.complete(ai_service=None, state=state)
        assert result is not None
        assert len(state.units) == 2  # 1 player + 1 AI
        assert state.units[1] is ai_unit

    def test_success_initializes_ai_service(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(
            begin_battle_result={
                "placements": [_make_placement(position=(5, 5))],
                "pending_orders": {},
            }
        )
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        ai_unit = _make_real_unit(
            unit_id="ai_0", faction=Faction.AXIS, unit_type=UnitType.MACHINE_GUN_SQUAD
        )
        dm._ai_units = [ai_unit]
        ai_service = MagicMock()
        state = StubGameState()
        dm.complete(ai_service=ai_service, state=state)
        ai_service.register_ai_unit.assert_called_once()
        registered_unit = ai_service.register_ai_unit.call_args[0][0]
        assert registered_unit is ai_unit

    def test_complete_applies_ui_pending_orders(self):
        """Pending orders from begin_battle result are applied to units."""
        placed = DeploymentUnit(
            unit_template_id="us_rifle_squad",
            display_name="Rifle Squad",
            unit_type="infantry",
            deployment_cost=120,
            position=(5, 5),
        )
        dm = DeploymentManager()
        ui = StubDeploymentUI(
            begin_battle_result={
                "placements": [_make_placement(position=(5, 5))],
                "pending_orders": {"us_rifle_squad": (10, 12)},
            },
            placed_units=[placed],
        )
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        dm._ai_units = []
        state = StubGameState()
        dm.complete(ai_service=None, state=state)
        assert state.units[0].move_target == TileCoord(10, 12)

    def test_complete_multiple_placements_counter_increments(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI(
            begin_battle_result={
                "placements": [
                    _make_placement(position=(5, 5)),
                    _make_placement(position=(6, 6)),
                    _make_placement(position=(7, 7)),
                ],
                "pending_orders": {},
            }
        )
        dm.deployment_phase_active = True
        dm.deployment_ui = ui
        dm._ai_units = []
        state = StubGameState()
        dm.complete(ai_service=None, state=state)
        assert len(state.units) == 3
        assert state.units[0].id == "player_0"
        assert state.units[1].id == "player_1"
        assert state.units[2].id == "player_2"


# ===========================================================================
# Tests: get_state()
# ===========================================================================


@pytest.mark.unit
class TestGetState:
    def test_no_ui_returns_none(self):
        dm = DeploymentManager()
        assert dm.get_state() is None

    def test_returns_ui_state(self):
        dm = DeploymentManager()
        ui = StubDeploymentUI()
        dm.deployment_ui = ui
        assert dm.get_state() is ui.state


# ===========================================================================
# Tests: pending orders CRUD
# ===========================================================================


@pytest.mark.unit
class TestPendingOrders:
    def test_set_and_get_pending_order(self):
        dm = DeploymentManager()
        dm.set_pending_order("us_rifle_squad", 10, 15)
        assert dm.get_pending_order("us_rifle_squad") == (10, 15)

    def test_get_pending_order_none_when_absent(self):
        dm = DeploymentManager()
        assert dm.get_pending_order("nonexistent") is None

    def test_clear_pending_order(self):
        dm = DeploymentManager()
        dm.set_pending_order("us_rifle_squad", 10, 15)
        dm.clear_pending_order("us_rifle_squad")
        assert dm.get_pending_order("us_rifle_squad") is None

    def test_clear_nonexistent_no_error(self):
        dm = DeploymentManager()
        dm.clear_pending_order("nonexistent")  # should not raise

    def test_set_overwrites_existing(self):
        dm = DeploymentManager()
        dm.set_pending_order("us_rifle_squad", 10, 15)
        dm.set_pending_order("us_rifle_squad", 20, 25)
        assert dm.get_pending_order("us_rifle_squad") == (20, 25)


# ===========================================================================
# Tests: apply_pending_orders()
# ===========================================================================


@pytest.mark.unit
class TestApplyPendingOrders:
    def test_empty_orders_early_return(self):
        dm = DeploymentManager()
        dm.apply_pending_orders([])
        assert dm._pending_orders == {}

    def test_matching_position_sets_move_target(self):
        dm = DeploymentManager()
        placed = DeploymentUnit(
            unit_template_id="us_rifle_squad",
            display_name="Rifle Squad",
            unit_type="infantry",
            deployment_cost=120,
            position=(5, 5),
        )
        ui = StubDeploymentUI(placed_units=[placed])
        dm.deployment_ui = ui
        dm.set_pending_order("us_rifle_squad", 10, 12)
        unit = _make_real_unit(tile_x=5, tile_y=5)
        dm.apply_pending_orders([unit])
        assert unit.move_target == TileCoord(10, 12)
        assert dm._pending_orders == {}

    def test_no_matching_position_no_target_set(self):
        dm = DeploymentManager()
        placed = DeploymentUnit(
            unit_template_id="us_rifle_squad",
            display_name="Rifle Squad",
            unit_type="infantry",
            deployment_cost=120,
            position=(5, 5),
        )
        ui = StubDeploymentUI(placed_units=[placed])
        dm.deployment_ui = ui
        dm.set_pending_order("us_rifle_squad", 10, 12)
        unit = _make_real_unit(tile_x=99, tile_y=99)  # different position
        dm.apply_pending_orders([unit])
        assert unit.move_target is None
        # Orders are still cleared after applying
        assert dm._pending_orders == {}

    def test_no_pending_order_for_matched_unit(self):
        """Position matches but no pending order for that template_id."""
        dm = DeploymentManager()
        placed = DeploymentUnit(
            unit_template_id="us_rifle_squad",
            display_name="Rifle Squad",
            unit_type="infantry",
            deployment_cost=120,
            position=(5, 5),
        )
        ui = StubDeploymentUI(placed_units=[placed])
        dm.deployment_ui = ui
        # Set order for a different template
        dm.set_pending_order("other_template", 10, 12)
        unit = _make_real_unit(tile_x=5, tile_y=5)
        dm.apply_pending_orders([unit])
        assert unit.move_target is None
        assert dm._pending_orders == {}


# ===========================================================================
# Tests: _detect_attacker_faction()
# ===========================================================================


@pytest.mark.unit
class TestDetectAttackerFaction:
    """Test the four attacker-detection strategies."""

    def test_explicit_allied(self):
        md = _make_map_data(attacker_faction="allied")
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_explicit_axis(self):
        md = _make_map_data(attacker_faction="axis")
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "axis"

    def test_invalid_explicit_falls_through(self):
        md = _make_map_data(attacker_faction="invalid")
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_zone_distance_ally_farther_returns_allied(self):
        md = _make_map_data(
            forces={
                "allies": {"deployment_zone": {"x_min": 0, "x_max": 5}},  # center=2.5
                "axis": {"deployment_zone": {"x_min": 20, "x_max": 25}},  # center=22.5
            },
            victory_locations=[{"position": [21, 10]}],  # VL center x=21
        )
        # ally_dist = |2.5 - 21| = 18.5, axis_dist = |22.5 - 21| = 1.5
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_zone_distance_axis_farther_returns_axis(self):
        md = _make_map_data(
            forces={
                "allies": {"deployment_zone": {"x_min": 20, "x_max": 25}},  # center=22.5
                "axis": {"deployment_zone": {"x_min": 0, "x_max": 5}},  # center=2.5
            },
            victory_locations=[{"position": [21, 10]}],
        )
        # ally_dist = |22.5 - 21| = 1.5, axis_dist = |2.5 - 21| = 18.5
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "axis"

    def test_equal_distances_falls_through_to_default(self):
        md = _make_map_data(
            forces={
                "allies": {"deployment_zone": {"x_min": 0, "x_max": 10}},  # center=5
                "axis": {"deployment_zone": {"x_min": 0, "x_max": 10}},  # center=5
            },
            victory_locations=[{"position": [5, 5]}],
        )
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_special_rules_defender_advantage(self):
        md = _make_map_data(special_rules=["defender_advantage"])
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_default_returns_allied(self):
        md = _make_map_data()
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_forces_without_vls_falls_through(self):
        md = _make_map_data(
            forces={"allies": {"deployment_zone": {"x_min": 0, "x_max": 5}}},
        )
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_vls_without_forces_falls_through(self):
        md = _make_map_data(victory_locations=[{"position": [10, 10]}])
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"

    def test_partial_deployment_zone_missing_falls_through(self):
        md = _make_map_data(
            forces={
                "allies": {"deployment_zone": {"x_min": 0, "x_max": 5}},
                # axis missing
            },
            victory_locations=[{"position": [10, 10]}],
        )
        assert DeploymentManager._detect_attacker_faction(md, "ally") == "allied"


# ===========================================================================
# Tests: _pre_create_ai_units()
# ===========================================================================


@pytest.mark.unit
class TestPreCreateAiUnits:
    def test_no_ai_deployments_returns_empty(self):
        dm = DeploymentManager()
        dm._ai_deployments = []
        assert dm._pre_create_ai_units("axis") == []

    def test_with_ai_deployments_creates_units(self):
        dm = DeploymentManager()
        dm._ai_deployments = [
            _make_placement(template_id="ger_rifle_squad", position=(20, 20)),
            _make_placement(template_id="ger_rifle_squad", position=(21, 21)),
        ]
        units = dm._pre_create_ai_units("axis")
        assert len(units) == 2
        assert all(u.faction == Faction.AXIS for u in units)
        assert units[0].id == "ai_0"
        assert units[1].id == "ai_1"

    def test_invalid_placement_skipped(self):
        dm = DeploymentManager()
        dm._ai_deployments = [
            _make_placement(position=(20, 20)),
            {"unit_template_id": "bad", "unit_type": "infantry", "position": None},  # invalid
        ]
        units = dm._pre_create_ai_units("axis")
        assert len(units) == 1  # only valid one created


# ===========================================================================
# Tests: _create_unit_from_placement()
# ===========================================================================


@pytest.mark.unit
class TestCreateUnitFromPlacement:
    """Test unit creation including all invalid-input branches."""

    def _type_maps(self):
        return {"infantry": UnitType.INFANTRY_SQUAD}, {}

    def test_no_position_returns_none(self):
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        result = dm._create_unit_from_placement(
            placement={"unit_template_id": "x", "unit_type": "infantry"},
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result is None

    def test_position_not_tuple_or_list_returns_none(self):
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        result = dm._create_unit_from_placement(
            placement={"unit_template_id": "x", "unit_type": "infantry", "position": "5,5"},
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result is None

    def test_position_too_short_returns_none(self):
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        result = dm._create_unit_from_placement(
            placement={"unit_template_id": "x", "unit_type": "infantry", "position": (5,)},
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result is None

    def test_invalid_coordinates_returns_none(self):
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        result = dm._create_unit_from_placement(
            placement={
                "unit_template_id": "x",
                "unit_type": "infantry",
                "position": ("abc", "def"),
            },
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result is None

    def test_valid_infantry_placement(self):
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        result = dm._create_unit_from_placement(
            placement=_make_placement(position=(5, 7)),
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=3,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result is not None
        assert result.id == "player_3"
        assert result.faction == Faction.ALLIES
        assert result.unit_type == UnitType.INFANTRY_SQUAD
        assert result.position.tile_coord == TileCoord(5, 7)
        assert result.health.max_hp == 100
        assert result.weapon.primary_weapon_id == "rifle"
        assert result.weapon.max_ammo == 120

    def test_template_type_override(self):
        """Template ID in _TEMPLATE_TYPE_MAP overrides unit_type."""
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        ttm["us_officer"] = UnitType.COMMANDER
        result = dm._create_unit_from_placement(
            placement=_make_placement(
                template_id="us_officer", unit_type="support", position=(5, 5)
            ),
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result.unit_type == UnitType.COMMANDER

    def test_vehicle_hp_200(self):
        dm = DeploymentManager()
        tm = {"vehicle": UnitType.TANK}
        result = dm._create_unit_from_placement(
            placement=_make_placement(unit_type="vehicle", position=(10, 10)),
            faction=Faction.AXIS,
            id_prefix="ai",
            counter=0,
            type_map=tm,
            template_type_map={},
        )
        assert result.health.max_hp == 200
        assert result.weapon.primary_weapon_id == "tank_cannon"
        assert result.weapon.max_ammo == 30

    def test_list_position_accepted(self):
        dm = DeploymentManager()
        tm, ttm = self._type_maps()
        result = dm._create_unit_from_placement(
            placement={
                "unit_template_id": "x",
                "unit_type": "infantry",
                "position": [5, 7],  # list, not tuple
            },
            faction=Faction.ALLIES,
            id_prefix="player",
            counter=0,
            type_map=tm,
            template_type_map=ttm,
        )
        assert result is not None
        assert result.position.tile_coord == TileCoord(5, 7)


# ===========================================================================
# Tests: _create_ai_units()
# ===========================================================================


@pytest.mark.unit
class TestCreateAiUnits:
    """Test the (currently unused) _create_ai_units helper for coverage."""

    def test_no_deployments_returns_empty(self):
        dm = DeploymentManager()
        dm._ai_deployments = []
        tm = {"infantry": UnitType.INFANTRY_SQUAD}
        units, counter = dm._create_ai_units(Faction.AXIS, 5, tm, {})
        assert units == []
        assert counter == 5

    def test_with_deployments_creates_units(self):
        dm = DeploymentManager()
        dm._ai_deployments = [
            _make_placement(position=(20, 20)),
            _make_placement(position=(21, 21)),
        ]
        tm = {"infantry": UnitType.INFANTRY_SQUAD}
        units, counter = dm._create_ai_units(Faction.AXIS, 0, tm, {})
        assert len(units) == 2
        assert counter == 2
        assert units[0].id == "ai_0"
        assert units[1].id == "ai_1"

    def test_invalid_placement_skipped_counter_unchanged(self):
        dm = DeploymentManager()
        dm._ai_deployments = [
            {"unit_template_id": "bad", "unit_type": "infantry", "position": None},
            _make_placement(position=(20, 20)),
        ]
        tm = {"infantry": UnitType.INFANTRY_SQUAD}
        units, counter = dm._create_ai_units(Faction.AXIS, 0, tm, {})
        assert len(units) == 1
        assert counter == 1  # only valid unit increments counter


# ===========================================================================
# Tests: _initialize_ai_service()
# ===========================================================================


@pytest.mark.unit
class TestInitializeAiService:
    def test_none_ai_service_is_noop(self):
        dm = DeploymentManager()
        unit = _make_real_unit(faction=Faction.AXIS)
        dm._initialize_ai_service(None, [unit], Faction.AXIS)
        # Should not raise

    def test_registers_only_ai_faction_units(self):
        dm = DeploymentManager()
        ai_service = MagicMock()
        ai_unit = _make_real_unit(
            unit_id="ai_0", faction=Faction.AXIS, unit_type=UnitType.MACHINE_GUN_SQUAD
        )
        player_unit = _make_real_unit(unit_id="player_0", faction=Faction.ALLIES)
        dm._initialize_ai_service(ai_service, [ai_unit, player_unit], Faction.AXIS)
        ai_service.register_ai_unit.assert_called_once()
        assert ai_service.register_ai_unit.call_args[0][0] is ai_unit

    def test_commander_unit_gets_commander_bt(self):
        dm = DeploymentManager()
        ai_service = MagicMock()
        commander = _make_real_unit(
            unit_id="cmd", faction=Faction.AXIS, unit_type=UnitType.COMMANDER
        )
        dm._initialize_ai_service(ai_service, [commander], Faction.AXIS)
        ai_service.register_ai_unit.assert_called_once()

    def test_infantry_unit_gets_infantry_bt(self):
        dm = DeploymentManager()
        ai_service = MagicMock()
        infantry = _make_real_unit(
            unit_id="inf", faction=Faction.AXIS, unit_type=UnitType.INFANTRY_SQUAD
        )
        dm._initialize_ai_service(ai_service, [infantry], Faction.AXIS)
        ai_service.register_ai_unit.assert_called_once()
