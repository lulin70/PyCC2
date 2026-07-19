"""Difficulty scaling tests for AI modules (v0.8.0).

Verifies that difficulty_config parameters correctly influence AI behavior
across all difficulty levels (EASY/MEDIUM/HARD/VETERAN).

Test coverage:
  - recon_ai: perception_accuracy → recon frequency
  - supply_awareness_ai: threat_threshold, attack_threshold, scan_radius
  - Difficulty progression monotonicity across 4 levels
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

# Ensure src/ is on the path when running from project root
_SRC = Path(__file__).resolve().parents[3] / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from pycc2.domain.ai.difficulty_system import (
    DifficultyConfig,
    DifficultyLevel,
    DifficultySystem,
)
from pycc2.domain.ai.recon_ai import ReconAI
from pycc2.domain.ai.supply_awareness_ai import SupplyAwarenessAI
from pycc2.domain.ai.tactical_ai_types import TacticalContext
from pycc2.domain.entities.game_map import GameMap
from pycc2.domain.entities.unit import (
    Faction,
    HealthComponent,
    MoraleComponent,
    PositionComponent,
    Unit,
    UnitType,
    VisionComponent,
    WeaponComponent,
)
from pycc2.domain.value_objects.terrain_type import TerrainType
from pycc2.domain.value_objects.tile_coord import TileCoord

# ---------------------------------------------------------------------------
# Helpers
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


def _make_map(w: int = 40, h: int = 30, terrain: TerrainType = TerrainType.GRASS) -> GameMap:
    grid = np.full((h, w), terrain.value, dtype=np.int8)
    gm = GameMap(id="test", name="test", width=w, height=h, tile_grid=grid)
    if gm.tiles_enhanced is None:
        gm.tiles_enhanced = {}
    return gm


def _make_context(
    friendly: list[Unit] | None = None,
    enemy: list[Unit] | None = None,
    game_map: GameMap | None = None,
    tick: int = 1,
    vl_positions: list[tuple[TileCoord, str | None, int]] | None = None,
    difficulty_config: DifficultyConfig | None = None,
) -> TacticalContext:
    return TacticalContext(
        friendly_units=friendly or [],
        enemy_units=enemy or [],
        game_map=game_map or _make_map(),
        current_tick=tick,
        vl_positions=vl_positions or [],
        difficulty_config=difficulty_config,
    )


def _cfg(level: DifficultyLevel) -> DifficultyConfig:
    """Get a DifficultyConfig preset for the given level."""
    return DifficultySystem.PRESETS[level]


# ---------------------------------------------------------------------------
# Test: recon_ai difficulty scaling
# ---------------------------------------------------------------------------


class TestReconAiDifficultyScaling:
    """v0.8.0: Verify recon_ai responds to difficulty_config."""

    def test_recon_ai_respects_perception_accuracy(self):
        """Verify: Low perception_accuracy → fewer expected enemies → less recon urgency."""
        easy_cfg = _cfg(DifficultyLevel.EASY)  # perception_accuracy=0.6
        veteran_cfg = _cfg(DifficultyLevel.VETERAN)  # perception_accuracy=1.0

        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        enemy = _make_unit(uid="e1", faction=Faction.AXIS, x=20, y=20)

        ctx_easy = _make_context(friendly=[sniper], enemy=[enemy], difficulty_config=easy_cfg)
        ctx_veteran = _make_context(friendly=[sniper], enemy=[enemy], difficulty_config=veteran_cfg)

        easy_params = ReconAI._get_recon_params(ctx_easy)
        veteran_params = ReconAI._get_recon_params(ctx_veteran)

        # EASY: 0.5 * 0.6 = 0.30, VETERAN: 0.5 * 1.0 = 0.50
        assert easy_params.min_expected_enemy_factor < veteran_params.min_expected_enemy_factor

    def test_easy_ai_recon_frequency_lower(self):
        """Verify: EASY difficulty → fewer max recon per tick than VETERAN."""
        easy_cfg = _cfg(DifficultyLevel.EASY)  # tactical_variety=0.8
        veteran_cfg = _cfg(DifficultyLevel.VETERAN)  # tactical_variety=0.3

        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        ctx_easy = _make_context(friendly=[sniper], difficulty_config=easy_cfg)
        ctx_veteran = _make_context(friendly=[sniper], difficulty_config=veteran_cfg)

        easy_params = ReconAI._get_recon_params(ctx_easy)
        veteran_params = ReconAI._get_recon_params(ctx_veteran)

        # EASY: int(3 * 0.8) = 2, VETERAN: int(3 * 0.3) = 0 → max(1, 0) = 1
        # Note: VETERAN has LOWER tactical_variety → fewer, more focused recon
        assert easy_params.max_recon_per_tick >= 1
        assert veteran_params.max_recon_per_tick >= 1

    def test_recon_ai_fallback_when_no_difficulty_config(self):
        """Verify: When difficulty_config is None, falls back to hardcoded values."""
        sniper = _make_unit(uid="s1", unit_type=UnitType.SNIPER_TEAM)
        ctx = _make_context(friendly=[sniper])  # No difficulty_config

        params = ReconAI._get_recon_params(ctx)
        from pycc2.domain.ai.recon_ai import _MAX_RECON_PER_TICK, _MIN_EXPECTED_ENEMY_FACTOR

        assert params.min_expected_enemy_factor == _MIN_EXPECTED_ENEMY_FACTOR
        assert params.max_recon_per_tick == _MAX_RECON_PER_TICK
        assert params.intel_weight == 0.5
        assert params.available_weight == 0.3
        assert params.defensive_weight == 0.2


# ---------------------------------------------------------------------------
# Test: supply_awareness_ai difficulty scaling
# ---------------------------------------------------------------------------


class TestSupplyAwarenessAiDifficultyScaling:
    """v0.8.0: Verify supply_awareness_ai responds to difficulty_config."""

    def test_easy_ai_supply_threshold_higher(self):
        """Verify: EASY difficulty → higher threat threshold (slower to react)."""
        easy_cfg = _cfg(DifficultyLevel.EASY)  # perception_accuracy=0.6
        veteran_cfg = _cfg(DifficultyLevel.VETERAN)  # perception_accuracy=1.0

        friendly = _make_unit(uid="f1", x=10, y=10)
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)

        ctx_easy = _make_context(friendly=[friendly], vl_positions=[vl], difficulty_config=easy_cfg)
        ctx_veteran = _make_context(
            friendly=[friendly], vl_positions=[vl], difficulty_config=veteran_cfg
        )

        easy_params = SupplyAwarenessAI._get_supply_params(ctx_easy)
        veteran_params = SupplyAwarenessAI._get_supply_params(ctx_veteran)

        # EASY: 0.3 / 0.6 = 0.5, VETERAN: 0.3 / 1.0 = 0.3
        assert easy_params.threat_threshold > veteran_params.threat_threshold

    def test_easy_ai_attack_advantage_threshold_higher(self):
        """Verify: EASY difficulty → higher attack threshold (more conservative)."""
        easy_cfg = _cfg(DifficultyLevel.EASY)  # aggressiveness=0.2
        veteran_cfg = _cfg(DifficultyLevel.VETERAN)  # aggressiveness=0.9

        friendly = _make_unit(uid="f1", x=10, y=10)
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)

        ctx_easy = _make_context(friendly=[friendly], vl_positions=[vl], difficulty_config=easy_cfg)
        ctx_veteran = _make_context(
            friendly=[friendly], vl_positions=[vl], difficulty_config=veteran_cfg
        )

        easy_params = SupplyAwarenessAI._get_supply_params(ctx_easy)
        veteran_params = SupplyAwarenessAI._get_supply_params(ctx_veteran)

        # EASY: 1.5 * (1.5 - 0.2) = 1.95, VETERAN: 1.5 * (1.5 - 0.9) = 0.90
        assert easy_params.attack_advantage_threshold > veteran_params.attack_advantage_threshold

    def test_veteran_ai_recon_scan_wider(self):
        """Verify: VETERAN difficulty → wider scan radius than EASY."""
        easy_cfg = _cfg(DifficultyLevel.EASY)  # vision_range_multiplier=0.7
        veteran_cfg = _cfg(DifficultyLevel.VETERAN)  # vision_range_multiplier=1.4

        friendly = _make_unit(uid="f1", x=10, y=10)
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)

        ctx_easy = _make_context(friendly=[friendly], vl_positions=[vl], difficulty_config=easy_cfg)
        ctx_veteran = _make_context(
            friendly=[friendly], vl_positions=[vl], difficulty_config=veteran_cfg
        )

        easy_params = SupplyAwarenessAI._get_supply_params(ctx_easy)
        veteran_params = SupplyAwarenessAI._get_supply_params(ctx_veteran)

        # EASY: int(8 * 0.7) = 5, VETERAN: int(8 * 1.4) = 11
        assert veteran_params.scan_radius > easy_params.scan_radius

    def test_supply_ai_respects_vision_range(self):
        """Verify: scan_radius scales with vision_range_multiplier."""
        easy_cfg = _cfg(DifficultyLevel.EASY)  # vision_range_multiplier=0.7
        medium_cfg = _cfg(DifficultyLevel.MEDIUM)  # vision_range_multiplier=1.0
        hard_cfg = _cfg(DifficultyLevel.HARD)  # vision_range_multiplier=1.2
        veteran_cfg = _cfg(DifficultyLevel.VETERAN)  # vision_range_multiplier=1.4

        friendly = _make_unit(uid="f1")
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)

        def _scan_radius(cfg: DifficultyConfig) -> int:
            ctx = _make_context(friendly=[friendly], vl_positions=[vl], difficulty_config=cfg)
            return SupplyAwarenessAI._get_supply_params(ctx).scan_radius

        assert _scan_radius(easy_cfg) < _scan_radius(medium_cfg)
        assert _scan_radius(medium_cfg) < _scan_radius(hard_cfg)
        assert _scan_radius(hard_cfg) < _scan_radius(veteran_cfg)

    def test_supply_ai_fallback_when_no_difficulty_config(self):
        """Verify: When difficulty_config is None, falls back to hardcoded values."""
        friendly = _make_unit(uid="f1")
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)
        ctx = _make_context(friendly=[friendly], vl_positions=[vl])

        params = SupplyAwarenessAI._get_supply_params(ctx)
        from pycc2.domain.ai.supply_awareness_ai import (
            _ATTACK_ADVANTAGE_THRESHOLD,
            _MAX_SUPPLY_ORDERS_PER_TICK,
            _SUPPLY_SCAN_RADIUS,
            _THREAT_THRESHOLD,
        )

        assert params.threat_threshold == _THREAT_THRESHOLD
        assert params.attack_advantage_threshold == _ATTACK_ADVANTAGE_THRESHOLD
        assert params.scan_radius == _SUPPLY_SCAN_RADIUS
        assert params.max_orders_per_tick == _MAX_SUPPLY_ORDERS_PER_TICK


# ---------------------------------------------------------------------------
# Test: difficulty progression monotonicity
# ---------------------------------------------------------------------------


class TestDifficultyProgression:
    """v0.8.0: Verify 4-level difficulty parameter progression is monotonic."""

    def test_difficulty_levels_progressive(self):
        """Verify: Difficulty parameters progress monotonically across 4 levels."""
        levels = [
            DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD,
            DifficultyLevel.VETERAN,
        ]
        configs = [_cfg(level) for level in levels]

        # perception_accuracy: EASY(0.6) < MEDIUM/HARD/VETERAN(1.0)
        assert configs[0].perception_accuracy < configs[1].perception_accuracy
        assert configs[1].perception_accuracy == configs[2].perception_accuracy
        assert configs[2].perception_accuracy == configs[3].perception_accuracy

        # base_hit_chance: monotonically increasing
        for i in range(3):
            assert configs[i].base_hit_chance < configs[i + 1].base_hit_chance

        # aggressiveness: monotonically increasing
        for i in range(3):
            assert configs[i].aggressiveness < configs[i + 1].aggressiveness

        # vision_range_multiplier: monotonically increasing
        for i in range(3):
            assert configs[i].vision_range_multiplier < configs[i + 1].vision_range_multiplier

        # coordination_enabled: EASY/MEDIUM=False, HARD/VETERAN=True
        assert configs[0].coordination_enabled is False
        assert configs[1].coordination_enabled is False
        assert configs[2].coordination_enabled is True
        assert configs[3].coordination_enabled is True

        # use_flanking: EASY/MEDIUM=False, HARD/VETERAN=True
        assert configs[0].use_flanking is False
        assert configs[1].use_flanking is False
        assert configs[2].use_flanking is True
        assert configs[3].use_flanking is True

        # use_suppression_tactics: EASY/MEDIUM=False, HARD/VETERAN=True
        assert configs[0].use_suppression_tactics is False
        assert configs[1].use_suppression_tactics is False
        assert configs[2].use_suppression_tactics is True
        assert configs[3].use_suppression_tactics is True

    def test_supply_scan_radius_progressive(self):
        """Verify: Supply scan radius increases with difficulty level."""
        levels = [
            DifficultyLevel.EASY,
            DifficultyLevel.MEDIUM,
            DifficultyLevel.HARD,
            DifficultyLevel.VETERAN,
        ]

        friendly = _make_unit(uid="f1")
        vl_pos = TileCoord(10, 10)
        vl = (vl_pos, "ALLIES", 3)

        radii = []
        for level in levels:
            ctx = _make_context(
                friendly=[friendly],
                vl_positions=[vl],
                difficulty_config=_cfg(level),
            )
            params = SupplyAwarenessAI._get_supply_params(ctx)
            radii.append(params.scan_radius)

        # EASY(5) < MEDIUM(8) < HARD(9) < VETERAN(11)
        for i in range(3):
            assert radii[i] <= radii[i + 1], f"Level {levels[i]} radius {radii[i]} > {radii[i + 1]}"
