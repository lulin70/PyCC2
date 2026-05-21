"""
AI configuration parameters for PyCC2.
Data-driven AI parameters replacing hardcoded magic numbers in CommanderAI and other AI modules.
"""

from __future__ import annotations

from dataclasses import dataclass, fields


@dataclass(slots=True)
class AIConfig:
    """Data-driven AI configuration organized by category."""

    # ── Thresholds (determine when AI makes decisions) ──
    retreat_force_ratio: float = 0.5
    cautious_force_ratio: float = 0.7
    low_morale_threshold: int = 30
    critical_morale_threshold: int = 15
    high_threat_distance: int = 8
    flank_min_units: int = 2

    # ── Weights (for scoring/evaluation) ──
    threat_distance_weight: float = 0.4
    threat_type_weight: float = 0.3
    threat_health_weight: float = 0.3
    vl_capture_priority: float = 0.8
    vl_defend_priority: float = 0.6

    # ── Timing (tick frequencies) ──
    commander_tick_hz: int = 2
    squad_leader_tick_hz: int = 4
    unit_tick_hz: int = 8
    game_ticks_per_second: int = 30

    # ── Behavior (tactical preferences) ──
    suppression_persistence: float = 0.7
    flank_aggression: float = 0.6
    infantry_tank_coord_range: int = 10
    at_ambush_patience: float = 0.8
    retreat_cover_priority: float = 0.7

    # ── Validation ──

    def validate(self) -> list[str]:
        """Return a list of validation error messages (empty if valid)."""
        errors: list[str] = []

        # Float weights must be in [0.0, 1.0]
        weight_fields = (
            "threat_distance_weight",
            "threat_type_weight",
            "threat_health_weight",
            "vl_capture_priority",
            "vl_defend_priority",
            "suppression_persistence",
            "flank_aggression",
            "at_ambush_patience",
            "retreat_cover_priority",
        )
        for name in weight_fields:
            value = getattr(self, name)
            if not (0.0 <= value <= 1.0):
                errors.append(f"{name}={value} must be between 0.0 and 1.0")

        # Thresholds must be positive
        positive_threshold_fields = (
            "retreat_force_ratio",
            "cautious_force_ratio",
            "low_morale_threshold",
            "critical_morale_threshold",
            "high_threat_distance",
            "flank_min_units",
            "infantry_tank_coord_range",
        )
        for name in positive_threshold_fields:
            value = getattr(self, name)
            if value <= 0:
                errors.append(f"{name}={value} must be positive")

        # Tick Hz must be positive
        tick_fields = (
            "commander_tick_hz",
            "squad_leader_tick_hz",
            "unit_tick_hz",
        )
        for name in tick_fields:
            value = getattr(self, name)
            if value <= 0:
                errors.append(f"{name}={value} must be positive")

        # game_ticks_per_second must be > 0
        if self.game_ticks_per_second <= 0:
            errors.append(f"game_ticks_per_second={self.game_ticks_per_second} must be > 0")

        return errors

    # ── Serialization ──

    def to_dict(self) -> dict:
        """Serialize to a plain dictionary."""
        return {f.name: getattr(self, f.name) for f in fields(self)}

    @classmethod
    def from_dict(cls, data: dict) -> AIConfig:
        """Deserialize from a dictionary, ignoring unknown keys."""
        valid_keys = {f.name for f in fields(cls)}
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    # ── Presets ──

    @classmethod
    def PRESET_EASY(cls) -> AIConfig:
        """Easy AI: slower decisions, less aggressive, less persistent."""
        return cls(
            retreat_force_ratio=0.7,
            cautious_force_ratio=0.85,
            low_morale_threshold=40,
            critical_morale_threshold=25,
            high_threat_distance=6,
            flank_min_units=3,
            threat_distance_weight=0.3,
            threat_type_weight=0.3,
            threat_health_weight=0.4,
            vl_capture_priority=0.5,
            vl_defend_priority=0.8,
            commander_tick_hz=1,
            squad_leader_tick_hz=2,
            unit_tick_hz=4,
            game_ticks_per_second=30,
            suppression_persistence=0.4,
            flank_aggression=0.3,
            infantry_tank_coord_range=8,
            at_ambush_patience=0.5,
            retreat_cover_priority=0.8,
        )

    @classmethod
    def PRESET_NORMAL(cls) -> AIConfig:
        """Normal AI: default values."""
        return cls()

    @classmethod
    def PRESET_HARD(cls) -> AIConfig:
        """Hard AI: faster decisions, more aggressive, more persistent."""
        return cls(
            retreat_force_ratio=0.35,
            cautious_force_ratio=0.55,
            low_morale_threshold=25,
            critical_morale_threshold=10,
            high_threat_distance=10,
            flank_min_units=2,
            threat_distance_weight=0.4,
            threat_type_weight=0.35,
            threat_health_weight=0.25,
            vl_capture_priority=0.9,
            vl_defend_priority=0.5,
            commander_tick_hz=3,
            squad_leader_tick_hz=6,
            unit_tick_hz=12,
            game_ticks_per_second=30,
            suppression_persistence=0.85,
            flank_aggression=0.8,
            infantry_tank_coord_range=12,
            at_ambush_patience=0.9,
            retreat_cover_priority=0.6,
        )

    @classmethod
    def PRESET_VETERAN(cls) -> AIConfig:
        """Veteran AI: fastest decisions, most aggressive, highest persistence."""
        return cls(
            retreat_force_ratio=0.2,
            cautious_force_ratio=0.4,
            low_morale_threshold=20,
            critical_morale_threshold=5,
            high_threat_distance=12,
            flank_min_units=1,
            threat_distance_weight=0.5,
            threat_type_weight=0.35,
            threat_health_weight=0.15,
            vl_capture_priority=1.0,
            vl_defend_priority=0.4,
            commander_tick_hz=4,
            squad_leader_tick_hz=8,
            unit_tick_hz=16,
            game_ticks_per_second=30,
            suppression_persistence=0.95,
            flank_aggression=0.95,
            infantry_tank_coord_range=14,
            at_ambush_patience=1.0,
            retreat_cover_priority=0.5,
        )
