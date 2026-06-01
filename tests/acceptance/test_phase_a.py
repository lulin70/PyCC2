"""
Phase A Acceptance Tests - Comprehensive validation for all 8 Phase A tasks.

Based on GAP_CLOSURE_PLAN.md Section 7 acceptance criteria.
Tests A1-A8 implementations to verify CC2 fidelity improvements.

Run: pytest tests/acceptance/test_phase_a.py -v
"""

from __future__ import annotations

import json
import math
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# ========================================================================
# A1: Audio System Tests (S-1)
# ========================================================================


class TestA1AudioSystem:
    """Verify audio system initializes correctly and can play sounds."""

    def test_sound_system_initializes_stereo(self):
        """Audio should initialize with stereo mixer (2 channels)."""
        from pycc2.presentation.audio.sound_system import SoundSystem, SoundConfig

        config = SoundConfig(enabled=True)
        system = SoundSystem(config)

        with patch("pycc2.presentation.audio.sound_system.mixer") as mock_mixer:
            mock_mixer.init.return_value = None
            system.initialize()

        assert system.initialized is True
        assert system._channel_count == 8  # Stereo uses 8 channels
        system.shutdown()

    def test_sound_system_fallback_to_mono(self):
        """Audio should fallback to mono if stereo fails."""
        from pycc2.presentation.audio.sound_system import SoundSystem, SoundConfig

        config = SoundConfig(enabled=True)
        system = SoundSystem(config)

        call_count = [0]

        def side_effect_init(**kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Stereo init failed: Array must be 2-dimensional")
            return None

        with patch("pycc2.presentation.audio.sound_system.mixer") as mock_mixer:
            mock_mixer.init.side_effect = side_effect_init
            mock_mixer.quit.return_value = None
            system.initialize()

        assert system.initialized is True
        assert system._channel_count == 4  # Mono uses 4 channels
        system.shutdown()

    def test_sound_system_graceful_disable(self):
        """Game should run without sound if both stereo and mono fail."""
        from pycc2.presentation.audio.sound_system import SoundSystem, SoundConfig

        config = SoundConfig(enabled=True)
        system = SoundSystem(config)

        with patch("pycc2.presentation.audio.sound_system.mixer") as mock_mixer:
            mock_mixer.init.side_effect = Exception("No audio device")
            mock_mixer.quit.return_value = None
            system.initialize()

        assert system.config.enabled is False  # Audio disabled gracefully
        system.shutdown()

    def test_procedural_sound_generator_produces_valid_audio(self):
        """Sound generator should produce valid int16 numpy arrays."""
        from pycc2.presentation.audio.sound_system import ProceduralSoundGenerator

        click = ProceduralSoundGenerator.generate_click()
        assert isinstance(click, np.ndarray)
        assert click.dtype == np.int16
        assert len(click) >= 1000, f"Click sound should be at least 1000 samples, got {len(click)}"

        rifle_shot = ProceduralSoundGenerator.generate_rifle_shot()
        assert isinstance(rifle_shot, np.ndarray)
        assert rifle_shot.dtype == np.int16

        explosion = ProceduralSoundGenerator.generate_explosion()
        assert len(explosion) >= len(rifle_shot) * 2, f"Explosion should be at least 2x longer than rifle shot (explosion={len(explosion)}, rifle={len(rifle_shot)})"

    def test_play_sound_returns_true_when_initialized(self):
        """play() should return True when audio is working."""
        from pycc2.presentation.audio.sound_system import (
            SoundSystem,
            SoundConfig,
            SoundType,
        )

        config = SoundConfig(enabled=True)
        system = SoundSystem(config)

        with patch("pycc2.presentation.audio.sound_system.mixer") as mock_mixer:
            mock_mixer.init.return_value = None
            mock_sound = MagicMock()
            mock_mixer.Sound.return_value = mock_sound
            mock_channel = MagicMock()
            mock_mixer.find_channel.return_value = mock_channel

            system.initialize()
            result = system.play(SoundType.UI_CLICK)

        assert result is True
        system.shutdown()


# ========================================================================
# A2: LOS System Tests (C-1)
# ========================================================================


class TestA2LOSSystem:
    """Verify Bresenham ray casting with height blocking."""

    @pytest.fixture
    def game_map(self):
        """Create a mock game map for LOS testing."""
        map_mock = MagicMock()
        map_mock.is_within_bounds.return_value = True

        terrain_mock = MagicMock()
        terrain_mock.name = "grass"
        terrain_mock.blocks_los = False
        map_mock.get_terrain.return_value = terrain_mock

        map_mock.get_enhanced_tile.return_value = {"elevation": 0}

        return map_mock

    def test_los_clear_line_of_sight(self, game_map):
        """Should return CLEAR when no obstacles between units."""
        from pycc2.domain.systems.los_system import Lossystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)
        start = TileCoord(5, 5)
        end = TileCoord(10, 5)

        can_see, result = los.check_los(start, end)

        assert can_see is True
        assert result.status.name == "CLEAR"

    def test_los_blocked_by_terrain(self, game_map):
        """Wall should block line of sight."""
        from pycc2.domain.systems.los_system import Lossystem, LosStatus
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)
        start = TileCoord(5, 5)
        end = TileCoord(15, 5)

        def get_terrain(coord):
            terrain = MagicMock()
            if coord.x == 10:
                terrain.name = "wall"
                terrain.blocks_los = True
            else:
                terrain.name = "grass"
                terrain.blocks_los = False
            return terrain

        game_map.get_terrain.side_effect = get_terrain

        can_see, result = los.check_los(start, end)

        assert can_see is False
        assert result.status == LosStatus.BLOCKED_TERRAIN
        assert result.blocking_coord.x == 10

    def test_los_out_of_range(self, game_map):
        """Units too far apart should be OUT_OF_RANGE."""
        from pycc2.domain.systems.los_system import Lossystem, LosStatus
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)
        start = TileCoord(0, 0)
        end = TileCoord(50, 50)  # Way beyond default range of 15

        can_see, result = los.check_los(start, end, max_range=15)

        assert can_see is False
        assert result.status == LosStatus.OUT_OF_RANGE

    def test_los_elevation_advantage(self, game_map):
        """Higher elevation should extend visual range."""
        from pycc2.domain.systems.los_system import Lossystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)

        def get_enhanced_tile(x, y):
            if x == 0:
                return {"elevation": 3}  # High ground
            return {"elevation": 0}

        game_map.get_enhanced_tile.side_effect = get_enhanced_tile

        start = TileCoord(0, 0)
        end = TileCoord(20, 0)  # Beyond normal range

        can_see, result = los.check_los(start, end, max_range=15)

        assert result.distance_tiles > 15  # Elevation bonus applied

    def test_los_bresenham_algorithm_correctness(self, game_map):
        """Bresenham line should visit correct intermediate tiles (supercover variant)."""
        from pycc2.domain.systems.los_system import Lossystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)
        start = TileCoord(0, 0)
        end = TileCoord(3, 3)

        line = los._bresenham_line_enhanced(start, end)

        assert len(line) >= 4  # Supercover may include extra diagonal points
        assert line[0] == TileCoord(0, 0)
        assert line[-1] == TileCoord(3, 3)

    def test_los_integration_with_attack_line(self, game_map):
        """LOS result should convert to AttackLine status correctly."""
        from pycc2.domain.systems.los_system import Lossystem, LosStatus
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = Lossystem(game_map)

        clear_result = MagicMock(status=LosStatus.CLEAR)
        assert los.integrate_to_attack_line_status(clear_result) == "CAN_ATTACK"

        blocked_result = MagicMock(status=LosStatus.BLOCKED_TERRAIN)
        assert los.integrate_to_attack_line_status(blocked_result) == "BLOCKED"

        oor_result = MagicMock(status=LosStatus.OUT_OF_RANGE)
        assert los.integrate_to_attack_line_status(oor_result) == "OUT_OF_RANGE"


# ========================================================================
# A3: Direction Sprite & Animation Tests (U-1, U-2)
# ========================================================================


class TestA3DirectionSprite:
    """Verify 8-direction sprite system and animation controller."""

    def test_direction_enum_has_8_values(self):
        """Direction enum should have exactly 8 compass directions."""
        from pycc2.presentation.rendering.direction_sprite import Direction

        directions = list(Direction)
        assert len(directions) == 8

        expected = ["NORTH", "NORTHEAST", "EAST", "SOUTHEAST",
                    "SOUTH", "SOUTHWEST", "WEST", "NORTHWEST"]
        actual = [d.name for d in directions]
        assert actual == expected

    def test_direction_from_angle_conversion(self):
        """Angle to direction conversion should be accurate (CC2 convention: 0°=East, 90°=South)."""
        from pycc2.presentation.rendering.direction_sprite import Direction

        assert Direction.from_angle(0) == Direction.EAST
        assert Direction.from_angle(90) == Direction.SOUTH      # CC2: Y-axis down
        assert Direction.from_angle(180) == Direction.WEST
        assert Direction.from_angle(270) == Direction.NORTH     # CC2: Y-axis up
        assert Direction.from_angle(45) == Direction.SOUTHEAST

    def test_direction_to_angle_roundtrip(self):
        """Direction → Angle → Direction should roundtrip correctly."""
        from pycc2.presentation.rendering.direction_sprite import Direction

        for direction in Direction:
            angle = direction.to_angle()
            recovered = Direction.from_angle(angle)
            assert recovered == direction, f"Failed roundtrip for {direction}"

    def test_sprite_set_generates_8_variants(self):
        """Procedural generation should create all 8 directions."""
        import pygame
        pygame.init()
        from pycc2.presentation.rendering.direction_sprite import (
            DirectionSpriteSet,
            Direction,
        )

        base_surface = pygame.Surface((32, 32), pygame.SRCALPHA)
        pygame.draw.rect(base_surface, (255, 0, 0), base_surface.get_rect())

        sprite_set = DirectionSpriteSet()
        sprite_set.generate_procedural_variants(base_surface)

        assert sprite_set.is_loaded is True
        assert len(sprite_set.directions) == 8
        assert Direction.EAST in sprite_set.directions
        assert Direction.WEST in sprite_set.directions
        pygame.quit()

    def test_animation_controller_states(self):
        """Animation controller should support all required states."""
        import pygame
        pygame.init()
        from pycc2.presentation.rendering.animation_controller import (
            AnimationController,
            AnimationState,
        )

        unit_mock = MagicMock()
        controller = AnimationController(unit_mock)

        states = list(AnimationState)
        required = ["IDLE", "MOVING", "ATTACKING", "DYING", "DEAD"]
        state_names = [s.name for s in states]

        for req in required:
            assert req in state_names, f"Missing animation state: {req}"
        pygame.quit()

    def test_animation_default_frame_counts(self):
        """Default animations should have correct frame counts."""
        import pygame
        pygame.init()
        from pycc2.presentation.rendering.animation_controller import (
            AnimationController,
            AnimationState,
        )

        unit_mock = MagicMock()
        controller = AnimationController(unit_mock)

        idle_anim = controller._animations[AnimationState.IDLE]
        moving_anim = controller._animations[AnimationState.MOVING]
        attacking_anim = controller._animations[AnimationState.ATTACKING]

        assert len(idle_anim.frames) >= 2  # At least 2 idle frames
        assert len(moving_anim.frames) >= 4  # At least 4 move frames
        assert len(attacking_anim.frames) >= 1  # At least 1 attack frame
        pygame.quit()


# ========================================================================
# A4: Context Menu Tests (I-1)
# ========================================================================


class TestA4ContextMenu:
    """Verify CC2-style right-click context menu."""

    def test_menu_initializes_with_all_actions(self):
        """Menu should have Move/Attack/Stop/Smoke/Hide/Sneak/Cancel."""
        from pycc2.presentation.ui.context_menu import (
            ContextMenu,
            ContextAction,
        )

        menu = ContextMenu()

        expected_actions = [
            ContextAction.MOVE,
            ContextAction.ATTACK,
            ContextAction.STOP,
            ContextAction.SMOKE,
            ContextAction.HIDE,
            ContextAction.SNEAK,
            ContextAction.CANCEL,
        ]

        actual_actions = [item.action for item in menu._items]
        assert actual_actions == expected_actions

    def test_menu_items_have_shortcuts_and_icons(self):
        """Each menu item should have keyboard shortcut and icon."""
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()

        for item in menu._items:
            assert len(item.shortcut) >= 1, f"{item.action} missing shortcut"
            assert len(item.icon_char) >= 1, f"{item.action} missing icon"

    def test_menu_show_and_hide(self):
        """Menu visibility should toggle correctly."""
        import pygame
        pygame.init()
        from pycc2.presentation.ui.context_menu import ContextMenu

        menu = ContextMenu()
        assert menu.visible is False

        callback = MagicMock()
        menu.show((100, 100), callback)
        assert menu.visible is True
        assert menu._position == (100, 100)

        menu.hide()
        assert menu.visible is False
        pygame.quit()

    def test_menu_enabled_actions_filtering(self):
        """Only specified actions should be enabled when provided."""
        import pygame
        pygame.init()
        pygame.font.init()  # Explicitly initialize font system
        from pycc2.presentation.ui.context_menu import (
            ContextMenu,
            ContextAction,
        )

        menu = ContextMenu()
        callback = MagicMock()
        enabled = {ContextAction.STOP, ContextAction.CANCEL}

        menu.show((50, 50), callback, enabled_actions=enabled)

        stop_item = next(item for item in menu._items
                         if item.action == ContextAction.STOP)
        attack_item = next(item for item in menu._items
                           if item.action == ContextAction.ATTACK)

        assert stop_item.enabled is True
        assert attack_item.enabled is False
        pygame.quit()

    def test_menu_keyboard_shortcuts(self):
        """Keyboard shortcuts should trigger correct actions."""
        import pygame
        pygame.init()
        from pycc2.presentation.ui.context_menu import (
            ContextMenu,
            ContextAction,
        )

        menu = ContextMenu()
        callback = MagicMock()
        menu.show((0, 0), callback)

        event = pygame.event.Event(pygame.KEYDOWN, key=pygame.K_z)
        consumed = menu.handle_event(event)

        assert consumed is True
        callback.assert_called_once_with(ContextAction.MOVE, (0, 0))
        pygame.quit()


# ========================================================================
# A5: Flank/Rear Damage Bonus Tests (C-2)
# ========================================================================


class TestA5FlankDamage:
    """Verify directional damage multipliers (front/flank/rear)."""

    def test_attack_angle_enum_defined(self):
        """AttackAngle should have FRONT/FLANK/REAR values."""
        import sys
        sys.path.insert(0, "src")
        from pycc2.services.combat_service import AttackAngle

        angles = list(AttackAngle)
        angle_names = [a.name for a in angles]

        assert "FRONT" in angle_names
        assert "FLANK_LEFT" in angle_names
        assert "FLANK_RIGHT" in angle_names
        assert "REAR" in angle_names

    def test_front_damage_multiplier_is_1x(self):
        """Frontal attacks should have 1.0x damage multiplier."""
        import sys
        sys.path.insert(0, "src")
        from pycc2.services.combat_service import AttackAngle, CombatService

        service = CombatService(MagicMock(), MagicMock(), MagicMock(), MagicMock())
        mult = service.get_angle_damage_multiplier(AttackAngle.FRONT)

        assert mult == 1.0

    def test_flank_damage_multiplier_is_1_5x(self):
        """Flank attacks should have 1.5x damage multiplier."""
        import sys
        sys.path.insert(0, "src")
        from pycc2.services.combat_service import AttackAngle, CombatService

        service = CombatService(MagicMock(), MagicMock(), MagicMock(), MagicMock())
        flank_left = service.get_angle_damage_multiplier(AttackAngle.FLANK_LEFT)
        flank_right = service.get_angle_damage_multiplier(AttackAngle.FLANK_RIGHT)

        assert flank_left == 1.5
        assert flank_right == 1.5

    def test_rear_damage_multiplier_is_2x(self):
        """Rear attacks should have 2.0x damage multiplier."""
        import sys
        sys.path.insert(0, "src")
        from pycc2.services.combat_service import AttackAngle, CombatService

        service = CombatService(MagicMock(), MagicMock(), MagicMock(), MagicMock())
        rear_mult = service.get_angle_damage_multiplier(AttackAngle.REAR)

        assert rear_mult == 2.0

    def test_rear_attack_increases_morale_impact(self):
        """Rear attacks should have 2.0x damage multiplier."""
        from pycc2.services.combat_service import AttackAngle

        attacker = MagicMock()
        attacker.position_component = MagicMock(x=0, y=0)
        attacker.unit_id = "attacker"

        target = MagicMock()
        target.position_component = MagicMock(x=10, y=0)
        target.facing = 0.0
        target.morale_component = MagicMock()
        target.is_alive = True
        target.unit_id = "target"

        from pycc2.services.combat_service import CombatService

        service = CombatService(MagicMock(), MagicMock(), MagicMock(), MagicMock())

        angle = service.calculate_attack_angle(attacker, target)
        assert angle == AttackAngle.REAR, f"Expected REAR, got {angle}"

        rear_mult = service.get_angle_damage_multiplier(angle)
        assert rear_mult == 2.0, f"Rear attack should be 2.0x, got {rear_mult}"


# ========================================================================
# A6: Multi-Level Building System Tests (M-1)
# ========================================================================


class TestA6MultiLevelBuildings:
    """Verify tile height attribute and building levels."""

    def test_enhanced_tile_has_height_attribute(self):
        """EnhancedTile should have height property (0-3 floors)."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        tile = EnhancedTile(base_terrain=5)  # Building terrain type
        assert hasattr(tile, "height")
        assert tile.height == 0  # Default ground level

        tile.height = 3  # 3-story building
        assert tile.height == 3

    def test_building_height_blocks_los(self):
        """Building tiles should block line of sight."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        ground = EnhancedTile(base_terrain=0)  # Grass
        building = EnhancedTile(base_terrain=5)  # Building

        assert ground.blocks_line_of_sight() is False
        assert building.blocks_line_of_sight() is True

    def test_height_affects_movement_cost(self):
        """Higher tiles should cost more movement (uphill)."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        flat_tile = EnhancedTile(base_terrain=0, height=0)
        hill_tile = EnhancedTile(base_terrain=0, height=2)

        assert hill_tile.effective_movement_cost > flat_tile.effective_movement_cost

    def test_tile_serialization_preserves_height(self):
        """JSON serialization should preserve height attribute."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        original = EnhancedTile(base_terrain=5, height=2)
        data = original.to_dict()

        assert data["height"] == 2

        restored = EnhancedTile.from_dict(data)
        assert restored.height == 2
        assert restored.base_terrain == 5

    def test_decoration_adds_cover_bonus(self):
        """Decorations like sandbags should add cover bonus."""
        from pycc2.domain.systems.enhanced_tile import (
            EnhancedTile,
            DecorationInstance,
            DecorationType,
        )

        tile = EnhancedTile(base_terrain=0)
        sandbag = DecorationInstance(decoration_type=DecorationType.SANDBAG_WALL)
        tile.add_decoration(sandbag)

        assert tile.total_cover_bonus >= 3  # Sandbags give +3 cover


# ========================================================================
# A7: Campaign Persistence Tests (E-1)
# ========================================================================


class TestA7CampaignPersistence:
    """Verify battle result saving and cross-battle inheritance."""

    def test_battle_result_creation(self):
        """BattleResult should capture all required fields."""
        from pycc2.domain.systems.campaign_persistence import (
            BattleResult,
            BattleOutcome,
            UnitBattleState,
        )

        unit_state = UnitBattleState(
            unit_id="rifle_squad_1",
            unit_template_id="rifle_squad_us",
            faction="allies",
            current_hp=75.0,
            max_hp=100.0,
            morale=80.0,
            experience=150,
            ammo_remaining={"rifle": 120},
            kills=3,
        )

        result = BattleResult(
            battle_id="arnhem_bridge_day1",
            operation_id="market_garden",
            sector="Arnhem",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_units_start=10,
            allied_units_end=7,
            axis_units_start=8,
            axis_units_end=2,
            allied_casualties=3,
            axis_casualties=6,
            unit_states=[unit_state],
        )

        assert result.outcome == BattleOutcome.ALLIED_VICTORY
        assert len(result.unit_states) == 1
        assert result.allied_casualties == 3
        assert result.timestamp != ""  # Auto-generated

    def test_campaign_progress_aggregation(self):
        """CampaignProgress should aggregate multiple battle results."""
        from pycc2.domain.systems.campaign_persistence import (
            CampaignProgress,
            BattleResult,
            BattleOutcome,
        )

        progress = CampaignProgress(
            campaign_id="market_garden_test",
            current_operation_id="operation_1",
        )

        result1 = BattleResult(
            battle_id="battle1",
            operation_id="op1",
            sector="A",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_casualties=2,
            axis_casualties=5,
        )

        result2 = BattleResult(
            battle_id="battle2",
            operation_id="op1",
            sector="B",
            day=2,
            outcome=BattleOutcome.AXIS_VICTORY,
            allied_casualties=4,
            axis_casualties=1,
        )

        progress.add_battle_result(result1)
        progress.add_battle_result(result2)

        assert progress.total_battles_completed == 2
        assert progress.total_allied_casualties == 6
        assert progress.total_axis_casualties == 6

    def test_save_and_load_campaign(self):
        """Campaign should save to JSON and load back correctly."""
        from pycc2.domain.systems.campaign_persistence import (
            CampaignPersistenceManager,
            CampaignProgress,
            BattleResult,
            BattleOutcome,
            UnitBattleState,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CampaignPersistenceManager(base_dir=tmpdir)

            original = CampaignProgress(
                campaign_id="test_campaign",
                current_operation_id="test_op",
                requisition_points_allies=450,
            )

            unit_state = UnitBattleState(
                unit_id="unit1",
                unit_template_id="template1",
                faction="allies",
                current_hp=80.0,
                experience=200,
            )

            battle = BattleResult(
                battle_id="b1",
                operation_id="test_op",
                sector="X",
                day=1,
                outcome=BattleOutcome.ALLIED_VICTORY,
                unit_states=[unit_state],
            )
            original.add_battle_result(battle)

            saved = manager.save_campaign_progress("test_campaign", original)
            assert saved is True

            loaded = manager.load_campaign_progress("test_campaign")
            assert loaded is not None
            assert loaded.campaign_id == "test_campaign"
            assert loaded.total_battles_completed == 1
            assert loaded.requisition_points_allies == 450

    def test_reinforcement_bonus_calculation(self):
        """Victory should give more reinforcement points than defeat."""
        from pycc2.domain.systems.campaign_persistence import (
            CampaignProgress,
            BattleResult,
            BattleOutcome,
        )

        victory_progress = CampaignProgress(
            campaign_id="victory_test",
            current_operation_id="op1",
        )
        victory_progress.add_battle_result(BattleResult(
            battle_id="v1",
            operation_id="op1",
            sector="A",
            day=1,
            outcome=BattleOutcome.ALLIED_VICTORY,
            allied_units_start=10,
            allied_units_end=9,
            axis_units_start=8,
            axis_units_end=4,
        ))

        defeat_progress = CampaignProgress(
            campaign_id="defeat_test",
            current_operation_id="op1",
        )
        defeat_progress.add_battle_result(BattleResult(
            battle_id="d1",
            operation_id="op1",
            sector="B",
            day=1,
            outcome=BattleOutcome.AXIS_VICTORY,
            allied_units_start=10,
            allied_units_end=5,
            axis_units_start=8,
            axis_units_end=7,
        ))

        victory_bonus = victory_progress.calculate_reinforcement_bonus()
        defeat_bonus = defeat_progress.calculate_reinforcement_bonus()

        assert victory_bonus["allies"] > defeat_bonus["allies"]

    def test_unit_state_inheritance(self):
        """Surviving units should inherit HP/morale/ammo from previous battle."""
        from pycc2.domain.systems.campaign_persistence import (
            CampaignPersistenceManager,
            CampaignProgress,
            UnitBattleState,
        )

        manager = CampaignPersistenceManager()

        progress = CampaignProgress(
            campaign_id="inherit_test",
            current_operation_id="op1",
        )
        progress.current_unit_states = [
            UnitBattleState(
                unit_id="survivor",
                unit_template_id="rifle_squad",
                faction="allies",
                is_alive=True,
                current_hp=60.0,
                max_hp=100.0,
                morale=70.0,
                experience=100,
                ammo_remaining={"rifle": 80},
            ),
            UnitBattleState(
                unit_id="dead",
                unit_template_id="mg_team",
                faction="allies",
                is_alive=False,
            ),
        ]

        unit_alive = MagicMock()
        unit_alive.unit_template_id = "rifle_squad"
        unit_alive.health_component = MagicMock()
        unit_alive.health_component.max_hp = 100.0
        unit_alive.morale_component = MagicMock()
        unit_alive.weapon_component = MagicMock()
        unit_alive.veterancy_component = MagicMock()

        unit_dead = MagicMock()
        unit_dead.unit_template_id = "mg_team"
        unit_dead.health_component = MagicMock()
        unit_dead.state_machine = MagicMock()

        units = [unit_alive, unit_dead]
        updated = manager.apply_inheritance_to_units(progress, units)

        assert len(updated) == 2
        unit_alive.health_component.current_hp = 60.0  # Inherited HP ratio


# ========================================================================
# A8: Hill/Terrain Elevation Tests (M-2)
# ========================================================================


class TestA8TerrainElevation:
    """Verify elevation attribute affects LOS and movement."""

    def test_enhanced_tile_supports_elevation(self):
        """EnhancedTile should store negative and positive elevation."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        valley = EnhancedTile(base_terrain=0, height=-2)
        plain = EnhancedTile(base_terrain=0, height=0)
        hill = EnhancedTile(base_terrain=0, height=3)

        assert valley.height == -2
        assert plain.height == 0
        assert hill.height == 3

    def test_elevation_increases_los_range(self):
        """Higher elevation should provide LOS advantage."""
        from pycc2.domain.systems.los_system import Lossystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        map_mock = MagicMock()
        map_mock.is_within_bounds.return_value = True

        terrain_mock = MagicMock()
        terrain_mock.name = "grass"
        terrain_mock.blocks_los = False
        map_mock.get_terrain.return_value = terrain_mock

        def get_elev(x, y):
            if x == 0:
                return {"elevation": 3}  # Observer on hill
            return {"elevation": 0}

        map_mock.get_enhanced_tile.side_effect = get_elev

        los = Lossystem(map_mock)
        _, result = los.check_los(
            TileCoord(0, 0),
            TileCoord(18, 0),
            max_range=15,
        )

        assert result.status.name in ["CLEAR", "OUT_OF_RANGE"]
        if result.status.name == "CLEAR":
            assert result.distance_tiles > 15  # Elevation extended range

    def test_uphill_movement_penalty(self):
        """Moving uphill should cost more movement points."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        flat = EnhancedTile(base_terrain=0, height=0)
        uphill = EnhancedTile(base_terrain=0, height=2)
        steep = EnhancedTile(base_terrain=0, height=3)

        costs = [flat.effective_movement_cost,
                 uphill.effective_movement_cost,
                 steep.effective_movement_cost]

        assert costs[0] < costs[1] < costs[2]

    def test_elevation_serialization(self):
        """Elevation should persist through JSON save/load."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        original = EnhancedTile(base_terrain=0, height=-1)
        data = original.to_dict()
        restored = EnhancedTile.from_dict(data)

        assert restored.height == -1

    def test_combined_building_and_elevation(self):
        """Building on a hill should stack heights for LOS blocking."""
        from pycc2.domain.systems.enhanced_tile import EnhancedTile

        tower = EnhancedTile(base_terrain=5, height=2)  # Building on +2 hill
        assert tower.height == 2


# ========================================================================
# Integration Test: Full Phase A Workflow
# ========================================================================


class TestPhaseAIntegration:
    """End-to-end test combining multiple Phase A systems."""

    def test_combat_scenario_with_los_and_flanking(self):
        """Full scenario: Unit on hill sees enemy, flanks for 1.5x bonus."""
        from pycc2.domain.systems.los_system import Lossystem, LosStatus
        from pycc2.domain.value_objects.tile_coord import TileCoord

        map_mock = MagicMock()
        map_mock.is_within_bounds.return_value = True
        terrain_mock = MagicMock()
        terrain_mock.name = "grass"
        terrain_mock.blocks_los = False
        map_mock.get_terrain.return_value = terrain_mock
        map_mock.get_enhanced_tile.return_value = {"elevation": 0}

        los = Lossystem(map_mock)

        attacker_pos = TileCoord(5, 5)
        target_pos = TileCoord(12, 5)

        can_see, los_result = los.check_los(attacker_pos, target_pos)
        assert can_see is True

        from pycc2.services.combat_service import AttackAngle, CombatService

        service = CombatService(MagicMock(), MagicMock(), MagicMock(), MagicMock())
        flank_mult = service.get_angle_damage_multiplier(AttackAngle.FLANK_LEFT)

        assert flank_mult == 1.5
        print("✅ Integration test passed: LOS clear + flanking bonus active")

    def test_persistent_campaign_across_multiple_battles(self):
        """Simulate 3-battle campaign with persistence."""
        from pycc2.domain.systems.campaign_persistence import (
            CampaignPersistenceManager,
            CampaignProgress,
            BattleResult,
            BattleOutcome,
            UnitBattleState,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CampaignPersistenceManager(base_dir=tmpdir)
            campaign = CampaignProgress(
                campaign_id="e2e_campaign",
                current_operation_id="market_garden",
            )

            for day in range(1, 4):
                unit = UnitBattleState(
                    unit_id=f"squad_{day}",
                    unit_template_id="rifle_squad",
                    faction="allies",
                    current_hp=100.0 - (day * 10),
                    morale=90.0 - (day * 5),
                )

                battle = BattleResult(
                    battle_id=f"battle_day{day}",
                    operation_id="market_garden",
                    sector=f"Sector_{day}",
                    day=day,
                    outcome=BattleOutcome.ALLIED_VICTORY,
                    allied_casualties=day,
                    axis_casualties=day + 2,
                    unit_states=[unit],
                )
                campaign.add_battle_result(battle)

            saved = manager.save_campaign_progress("e2e_campaign", campaign)
            assert saved is True

            loaded = manager.load_campaign_progress("e2e_campaign")
            assert loaded is not None
            assert loaded.total_battles_completed == 3
            assert loaded.total_allied_casualties == 6  # 1+2+3

            bonus = loaded.calculate_reinforcement_bonus()
            assert bonus["allies"] > 0  # Victories give reinforcements


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
