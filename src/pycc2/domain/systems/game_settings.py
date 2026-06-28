"""CC2-Style New Game Settings System

Implements the classic Close Combat 2 feature where at the start of a new
campaign, the player can independently adjust experience level and supply
level for BOTH sides (allied and axis).

Key CC2 mechanics modeled:
  - Experience level affects: accuracy, morale, panic threshold, reaction speed
  - Supply level affects: ammo replenishment, reinforcements, morale recovery
  - Five difficulty presets combine both sides' settings
  - Settings are applied to campaign, units, supply state, and AI difficulty
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pycc2.domain.ai.difficulty_system import DifficultyConfig, DifficultyLevel
    from pycc2.domain.systems.campaign_four_layer import GrandCampaignDefinition
    from pycc2.domain.systems.supply_line import SupplyState


# ========================================================================
# Enums
# ========================================================================


class ExperienceLevel(Enum):
    """Experience tiers that tune unit accuracy, morale, and reaction speed."""

    CONSCRIPT = auto()
    REGULAR = auto()
    VETERAN = auto()
    ELITE = auto()


class SupplyLevelSetting(Enum):
    """Supply tiers that govern ammo, reinforcements, and morale recovery."""

    ABUNDANT = auto()
    ADEQUATE = auto()
    SCARCE = auto()
    CRITICAL = auto()


class GamePreset(Enum):
    """Named difficulty presets bundling per-side experience and supply levels."""

    RECRUIT = auto()
    EASY = auto()
    NORMAL = auto()
    HARD = auto()
    VETERAN = auto()


# ========================================================================
# Settings Dataclasses
# ========================================================================


@dataclass(frozen=True, slots=True)
class SideSettings:
    """Per-side experience and supply level selections."""

    experience_level: ExperienceLevel
    supply_level: SupplyLevelSetting


@dataclass(frozen=True, slots=True)
class GameSettings:
    """Top-level game settings combining both sides' experience and supply."""

    allied_settings: SideSettings
    axis_settings: SideSettings
    campaign_id: str = "market_garden"
    player_side: str = "allied"


# ========================================================================
# Effects Dataclasses
# ========================================================================


@dataclass(frozen=True, slots=True)
class ExperienceLevelEffects:
    """Numeric modifiers derived from an experience level."""

    accuracy_modifier: float
    morale_resistance: float
    panic_threshold_modifier: float
    reaction_speed_modifier: float
    starting_xp: int
    suppression_recovery_modifier: float


@dataclass(frozen=True, slots=True)
class SupplyLevelEffects:
    """Numeric modifiers derived from a supply level."""

    ammo_replenishment_rate: float
    reinforcement_rate: float
    morale_recovery_rate: float
    requisition_point_modifier: float
    starting_ammo_modifier: float


# ========================================================================
# Effects Lookup Tables
# ========================================================================

EXPERIENCE_EFFECTS: dict[ExperienceLevel, ExperienceLevelEffects] = {
    ExperienceLevel.CONSCRIPT: ExperienceLevelEffects(
        accuracy_modifier=0.75,
        morale_resistance=0.7,
        panic_threshold_modifier=1.3,
        reaction_speed_modifier=0.8,
        starting_xp=0,
        suppression_recovery_modifier=0.7,
    ),
    ExperienceLevel.REGULAR: ExperienceLevelEffects(
        accuracy_modifier=1.0,
        morale_resistance=1.0,
        panic_threshold_modifier=1.0,
        reaction_speed_modifier=1.0,
        starting_xp=100,
        suppression_recovery_modifier=1.0,
    ),
    ExperienceLevel.VETERAN: ExperienceLevelEffects(
        accuracy_modifier=1.15,
        morale_resistance=1.2,
        panic_threshold_modifier=0.8,
        reaction_speed_modifier=1.1,
        starting_xp=300,
        suppression_recovery_modifier=1.2,
    ),
    ExperienceLevel.ELITE: ExperienceLevelEffects(
        accuracy_modifier=1.25,
        morale_resistance=1.4,
        panic_threshold_modifier=0.6,
        reaction_speed_modifier=1.2,
        starting_xp=600,
        suppression_recovery_modifier=1.4,
    ),
}

SUPPLY_EFFECTS: dict[SupplyLevelSetting, SupplyLevelEffects] = {
    SupplyLevelSetting.ABUNDANT: SupplyLevelEffects(
        ammo_replenishment_rate=1.0,
        reinforcement_rate=1.0,
        morale_recovery_rate=0.8,
        requisition_point_modifier=1.2,
        starting_ammo_modifier=1.0,
    ),
    SupplyLevelSetting.ADEQUATE: SupplyLevelEffects(
        ammo_replenishment_rate=0.75,
        reinforcement_rate=0.8,
        morale_recovery_rate=0.6,
        requisition_point_modifier=1.0,
        starting_ammo_modifier=0.9,
    ),
    SupplyLevelSetting.SCARCE: SupplyLevelEffects(
        ammo_replenishment_rate=0.5,
        reinforcement_rate=0.5,
        morale_recovery_rate=0.4,
        requisition_point_modifier=0.8,
        starting_ammo_modifier=0.75,
    ),
    SupplyLevelSetting.CRITICAL: SupplyLevelEffects(
        ammo_replenishment_rate=0.25,
        reinforcement_rate=0.2,
        morale_recovery_rate=0.15,
        requisition_point_modifier=0.5,
        starting_ammo_modifier=0.5,
    ),
}


# ========================================================================
# Preset Configurations (matching CC2)
# ========================================================================

GAME_PRESETS: dict[GamePreset, GameSettings] = {
    GamePreset.RECRUIT: GameSettings(
        allied_settings=SideSettings(
            experience_level=ExperienceLevel.VETERAN,
            supply_level=SupplyLevelSetting.ABUNDANT,
        ),
        axis_settings=SideSettings(
            experience_level=ExperienceLevel.CONSCRIPT,
            supply_level=SupplyLevelSetting.SCARCE,
        ),
    ),
    GamePreset.EASY: GameSettings(
        allied_settings=SideSettings(
            experience_level=ExperienceLevel.REGULAR,
            supply_level=SupplyLevelSetting.ADEQUATE,
        ),
        axis_settings=SideSettings(
            experience_level=ExperienceLevel.CONSCRIPT,
            supply_level=SupplyLevelSetting.SCARCE,
        ),
    ),
    GamePreset.NORMAL: GameSettings(
        allied_settings=SideSettings(
            experience_level=ExperienceLevel.REGULAR,
            supply_level=SupplyLevelSetting.ADEQUATE,
        ),
        axis_settings=SideSettings(
            experience_level=ExperienceLevel.REGULAR,
            supply_level=SupplyLevelSetting.ADEQUATE,
        ),
    ),
    GamePreset.HARD: GameSettings(
        allied_settings=SideSettings(
            experience_level=ExperienceLevel.REGULAR,
            supply_level=SupplyLevelSetting.SCARCE,
        ),
        axis_settings=SideSettings(
            experience_level=ExperienceLevel.VETERAN,
            supply_level=SupplyLevelSetting.ADEQUATE,
        ),
    ),
    GamePreset.VETERAN: GameSettings(
        allied_settings=SideSettings(
            experience_level=ExperienceLevel.CONSCRIPT,
            supply_level=SupplyLevelSetting.CRITICAL,
        ),
        axis_settings=SideSettings(
            experience_level=ExperienceLevel.ELITE,
            supply_level=SupplyLevelSetting.ABUNDANT,
        ),
    ),
}


# ========================================================================
# ExperienceLevel -> DifficultyLevel mapping
# ========================================================================

_EXPERIENCE_TO_DIFFICULTY: dict[ExperienceLevel, DifficultyLevel] | None = None


def _get_experience_to_difficulty_map() -> dict[ExperienceLevel, DifficultyLevel]:
    global _EXPERIENCE_TO_DIFFICULTY
    if _EXPERIENCE_TO_DIFFICULTY is None:
        from pycc2.domain.ai.difficulty_system import DifficultyLevel as DL

        _EXPERIENCE_TO_DIFFICULTY = {
            ExperienceLevel.CONSCRIPT: DL.EASY,
            ExperienceLevel.REGULAR: DL.MEDIUM,
            ExperienceLevel.VETERAN: DL.HARD,
            ExperienceLevel.ELITE: DL.VETERAN,
        }
    return _EXPERIENCE_TO_DIFFICULTY


# ========================================================================
# GameSettingsApplier
# ========================================================================


class GameSettingsApplier:
    """Applies GameSettings to the game world.

    Modifies campaign requisition points, unit XP/ammo, supply rates,
    and AI difficulty based on the per-side experience and supply settings.
    """

    def __init__(self, settings: GameSettings) -> None:
        """Initialize the applier with the game settings to apply."""
        self._settings = settings

    @property
    def settings(self) -> GameSettings:
        """Return the game settings applied by this applier."""
        return self._settings

    def get_experience_effects(self, side: str) -> ExperienceLevelEffects:
        """Return the experience-level effects for the given side."""
        side_settings = self._get_side_settings(side)
        return EXPERIENCE_EFFECTS[side_settings.experience_level]

    def get_supply_effects(self, side: str) -> SupplyLevelEffects:
        """Return the supply-level effects for the given side."""
        side_settings = self._get_side_settings(side)
        return SUPPLY_EFFECTS[side_settings.supply_level]

    def apply_to_campaign(self, campaign: GrandCampaignDefinition) -> GrandCampaignDefinition:
        """Modify requisition points based on supply level for each side."""
        allied_supply = self.get_supply_effects("allied")
        axis_supply = self.get_supply_effects("axis")

        modified_sectors = []
        for sector in campaign.sectors:
            modified_ops = []
            for op in sector.operations:
                new_allied_rp = int(
                    op.requisition_points_allies * allied_supply.requisition_point_modifier
                )
                new_axis_rp = int(
                    op.requisition_points_axis * axis_supply.requisition_point_modifier
                )
                modified_ops.append(
                    dataclasses.replace(
                        op,
                        requisition_points_allies=new_allied_rp,
                        requisition_points_axis=new_axis_rp,
                    )
                )
            modified_sectors.append(dataclasses.replace(sector, operations=modified_ops))

        return dataclasses.replace(campaign, sectors=modified_sectors)

    def apply_to_unit(self, unit: object, side: str) -> None:
        """Set initial XP and ammo on a unit based on experience/supply settings."""
        exp_effects = self.get_experience_effects(side)
        supply_effects = self.get_supply_effects(side)

        # Set veterancy XP if the unit has a veterancy component
        veterancy = getattr(unit, "veterancy", None)
        if veterancy is not None and hasattr(veterancy, "add_xp"):
            veterancy.add_xp(exp_effects.starting_xp)

        # Scale starting ammo if the unit has a weapon component
        weapon = getattr(unit, "weapon", None)
        if weapon is not None:
            new_ammo = max(1, int(weapon.max_ammo * supply_effects.starting_ammo_modifier))
            weapon.ammo_remaining = new_ammo

    def apply_to_supply_state(self, supply_state: SupplyState, side: str) -> None:
        """Modify supply rates based on the side's supply level setting."""
        supply_effects = self.get_supply_effects(side)
        supply_state.ammo_replenishment_rate *= supply_effects.ammo_replenishment_rate
        supply_state.reinforcement_rate *= supply_effects.reinforcement_rate
        supply_state.morale_recovery_rate *= supply_effects.morale_recovery_rate

    def apply_to_difficulty_config(
        self, difficulty_config: DifficultyConfig, side: str
    ) -> DifficultyConfig:
        """Map experience level to AI difficulty and return modified config."""
        from pycc2.domain.ai.difficulty_system import DifficultySystem

        side_settings = self._get_side_settings(side)
        mapping = _get_experience_to_difficulty_map()
        target_level = mapping[side_settings.experience_level]

        # Use the preset config for that difficulty level
        preset_config = DifficultySystem.PRESETS[target_level]

        # Apply experience-level accuracy modifier on top of the preset
        exp_effects = self.get_experience_effects(side)
        modified_base_hit = max(
            0.05, min(0.95, preset_config.base_hit_chance * exp_effects.accuracy_modifier)
        )
        modified_morale = preset_config.morale_stability * exp_effects.morale_resistance

        return dataclasses.replace(
            preset_config,
            level=target_level,
            base_hit_chance=modified_base_hit,
            morale_stability=modified_morale,
        )

    def _get_side_settings(self, side: str) -> SideSettings:
        if side == "allied":
            return self._settings.allied_settings
        return self._settings.axis_settings
