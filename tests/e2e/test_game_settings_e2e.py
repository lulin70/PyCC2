"""
E2E tests for the GameSettings system — CC2-style new game settings.

Validates that difficulty presets, experience/supply effects, and the
GameSettingsApplier all integrate correctly with campaign, supply,
and AI difficulty subsystems. No pygame required.
"""

from __future__ import annotations

import pytest

from pycc2.domain.ai.difficulty_system import DifficultyConfig, DifficultyLevel, DifficultySystem
from pycc2.domain.systems.campaign_four_layer import (
    GrandCampaignDefinition,
    OperationDefinition,
    SectorCampaignDefinition,
    create_market_garden_campaign,
)
from pycc2.domain.systems.game_settings import (
    EXPERIENCE_EFFECTS,
    GAME_PRESETS,
    SUPPLY_EFFECTS,
    ExperienceLevel,
    GamePreset,
    GameSettings,
    GameSettingsApplier,
    SideSettings,
    SupplyLevelSetting,
)
from pycc2.domain.systems.supply_line import SupplyState, SupplyType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def campaign() -> GrandCampaignDefinition:
    return create_market_garden_campaign()


@pytest.fixture()
def applier_normal() -> GameSettingsApplier:
    return GameSettingsApplier(GAME_PRESETS[GamePreset.NORMAL])


@pytest.fixture()
def applier_hard() -> GameSettingsApplier:
    return GameSettingsApplier(GAME_PRESETS[GamePreset.HARD])


@pytest.fixture()
def applier_veteran() -> GameSettingsApplier:
    return GameSettingsApplier(GAME_PRESETS[GamePreset.VETERAN])


# ---------------------------------------------------------------------------
# 1. Preset: RECRUIT
# ---------------------------------------------------------------------------

class TestGamePresetRecruit:
    def test_game_preset_recruit(self) -> None:
        settings = GAME_PRESETS[GamePreset.RECRUIT]
        # Allied: VETERAN experience + ABUNDANT supply
        assert settings.allied_settings.experience_level == ExperienceLevel.VETERAN
        assert settings.allied_settings.supply_level == SupplyLevelSetting.ABUNDANT
        # Axis: CONSCRIPT experience + SCARCE supply
        assert settings.axis_settings.experience_level == ExperienceLevel.CONSCRIPT
        assert settings.axis_settings.supply_level == SupplyLevelSetting.SCARCE


# ---------------------------------------------------------------------------
# 2. Preset: NORMAL
# ---------------------------------------------------------------------------

class TestGamePresetNormal:
    def test_game_preset_normal(self) -> None:
        settings = GAME_PRESETS[GamePreset.NORMAL]
        # Both sides: REGULAR experience + ADEQUATE supply
        assert settings.allied_settings.experience_level == ExperienceLevel.REGULAR
        assert settings.allied_settings.supply_level == SupplyLevelSetting.ADEQUATE
        assert settings.axis_settings.experience_level == ExperienceLevel.REGULAR
        assert settings.axis_settings.supply_level == SupplyLevelSetting.ADEQUATE


# ---------------------------------------------------------------------------
# 3. Preset: VETERAN
# ---------------------------------------------------------------------------

class TestGamePresetVeteran:
    def test_game_preset_veteran(self) -> None:
        settings = GAME_PRESETS[GamePreset.VETERAN]
        # Allied: CONSCRIPT experience + CRITICAL supply
        assert settings.allied_settings.experience_level == ExperienceLevel.CONSCRIPT
        assert settings.allied_settings.supply_level == SupplyLevelSetting.CRITICAL
        # Axis: ELITE experience + ABUNDANT supply
        assert settings.axis_settings.experience_level == ExperienceLevel.ELITE
        assert settings.axis_settings.supply_level == SupplyLevelSetting.ABUNDANT


# ---------------------------------------------------------------------------
# 4. Custom settings
# ---------------------------------------------------------------------------

class TestCustomSettings:
    def test_custom_settings(self) -> None:
        custom = GameSettings(
            allied_settings=SideSettings(
                experience_level=ExperienceLevel.ELITE,
                supply_level=SupplyLevelSetting.CRITICAL,
            ),
            axis_settings=SideSettings(
                experience_level=ExperienceLevel.CONSCRIPT,
                supply_level=SupplyLevelSetting.ABUNDANT,
            ),
            campaign_id="custom_campaign",
            player_side="axis",
        )
        assert custom.allied_settings.experience_level == ExperienceLevel.ELITE
        assert custom.allied_settings.supply_level == SupplyLevelSetting.CRITICAL
        assert custom.axis_settings.experience_level == ExperienceLevel.CONSCRIPT
        assert custom.axis_settings.supply_level == SupplyLevelSetting.ABUNDANT
        assert custom.campaign_id == "custom_campaign"
        assert custom.player_side == "axis"


# ---------------------------------------------------------------------------
# 5. Experience effects: CONSCRIPT
# ---------------------------------------------------------------------------

class TestExperienceEffectsConscript:
    def test_experience_effects_conscript(self) -> None:
        effects = EXPERIENCE_EFFECTS[ExperienceLevel.CONSCRIPT]
        assert effects.accuracy_modifier == 0.75
        assert effects.morale_resistance == 0.7
        assert effects.starting_xp == 0


# ---------------------------------------------------------------------------
# 6. Experience effects: ELITE
# ---------------------------------------------------------------------------

class TestExperienceEffectsElite:
    def test_experience_effects_elite(self) -> None:
        effects = EXPERIENCE_EFFECTS[ExperienceLevel.ELITE]
        assert effects.accuracy_modifier == 1.25
        assert effects.morale_resistance == 1.4
        assert effects.starting_xp == 600


# ---------------------------------------------------------------------------
# 7. Supply effects: ABUNDANT
# ---------------------------------------------------------------------------

class TestSupplyEffectsAbundant:
    def test_supply_effects_abundant(self) -> None:
        effects = SUPPLY_EFFECTS[SupplyLevelSetting.ABUNDANT]
        assert effects.ammo_replenishment_rate == 1.0
        assert effects.reinforcement_rate == 1.0
        assert effects.requisition_point_modifier == 1.2


# ---------------------------------------------------------------------------
# 8. Supply effects: CRITICAL
# ---------------------------------------------------------------------------

class TestSupplyEffectsCritical:
    def test_supply_effects_critical(self) -> None:
        effects = SUPPLY_EFFECTS[SupplyLevelSetting.CRITICAL]
        assert effects.ammo_replenishment_rate == 0.25
        assert effects.reinforcement_rate == 0.2
        assert effects.requisition_point_modifier == 0.5


# ---------------------------------------------------------------------------
# 9. Applier modifies campaign requisition points
# ---------------------------------------------------------------------------

class TestApplierModifiesCampaignRequisition:
    def test_applier_modifies_campaign_requisition(
        self, campaign: GrandCampaignDefinition, applier_normal: GameSettingsApplier,
    ) -> None:
        # NORMAL preset: both sides ADEQUATE → requisition modifier = 1.0
        modified = applier_normal.apply_to_campaign(campaign)
        for sector in modified.sectors:
            for op in sector.operations:
                # With modifier 1.0, int(rp * 1.0) == original rp
                original_op = next(
                    o for s in campaign.sectors for o in s.operations
                    if o.operation_id == op.operation_id
                )
                assert op.requisition_points_allies == original_op.requisition_points_allies
                assert op.requisition_points_axis == original_op.requisition_points_axis


# ---------------------------------------------------------------------------
# 10. Applier modifies supply state
# ---------------------------------------------------------------------------

class TestApplierModifiesSupplyState:
    def test_applier_modifies_supply_state(self, applier_hard: GameSettingsApplier) -> None:
        # HARD: allied=SCARCE, axis=ADEQUATE
        allied_supply = SupplyState(
            sector_id="arnhem", day=1,
            supply_type=SupplyType.AIRDROP,
            ammo_replenishment_rate=1.0,
            reinforcement_rate=1.0,
            morale_recovery_rate=1.0,
        )
        applier_hard.apply_to_supply_state(allied_supply, "allied")

        # SCARCE: ammo=0.5, reinforcement=0.5, morale=0.4
        assert allied_supply.ammo_replenishment_rate == pytest.approx(0.5)
        assert allied_supply.reinforcement_rate == pytest.approx(0.5)
        assert allied_supply.morale_recovery_rate == pytest.approx(0.4)


# ---------------------------------------------------------------------------
# 11. Applier maps experience to AI difficulty
# ---------------------------------------------------------------------------

class TestApplierMapsExperienceToDifficulty:
    def test_applier_maps_experience_to_difficulty(self) -> None:
        # CONSCRIPT → EASY AI
        conscript_settings = GameSettings(
            allied_settings=SideSettings(
                experience_level=ExperienceLevel.CONSCRIPT,
                supply_level=SupplyLevelSetting.ADEQUATE,
            ),
            axis_settings=SideSettings(
                experience_level=ExperienceLevel.ELITE,
                supply_level=SupplyLevelSetting.ADEQUATE,
            ),
        )
        applier = GameSettingsApplier(conscript_settings)

        allied_config = applier.apply_to_difficulty_config(
            DifficultyConfig(level=DifficultyLevel.MEDIUM), "allied",
        )
        assert allied_config.level == DifficultyLevel.EASY

        # ELITE → VETERAN AI
        axis_config = applier.apply_to_difficulty_config(
            DifficultyConfig(level=DifficultyLevel.MEDIUM), "axis",
        )
        assert axis_config.level == DifficultyLevel.VETERAN


# ---------------------------------------------------------------------------
# 12. HARD preset favors axis
# ---------------------------------------------------------------------------

class TestHardPresetFavorsAxis:
    def test_hard_preset_favors_axis(self) -> None:
        settings = GAME_PRESETS[GamePreset.HARD]
        # Axis has better experience
        assert settings.axis_settings.experience_level.value > settings.allied_settings.experience_level.value
        # Axis has better supply
        assert settings.axis_settings.supply_level.value < settings.allied_settings.supply_level.value
        # (Lower SupplyLevelSetting enum value = better supply: ABUNDANT=1, ADEQUATE=2, SCARCE=3, CRITICAL=4)


# ---------------------------------------------------------------------------
# 13. All presets have both sides
# ---------------------------------------------------------------------------

class TestAllPresetsHaveBothSides:
    def test_all_presets_have_both_sides(self) -> None:
        for preset in GamePreset:
            settings = GAME_PRESETS[preset]
            assert settings.allied_settings is not None
            assert settings.axis_settings is not None
            assert isinstance(settings.allied_settings.experience_level, ExperienceLevel)
            assert isinstance(settings.allied_settings.supply_level, SupplyLevelSetting)
            assert isinstance(settings.axis_settings.experience_level, ExperienceLevel)
            assert isinstance(settings.axis_settings.supply_level, SupplyLevelSetting)


# ---------------------------------------------------------------------------
# 14. Settings affect campaign flow
# ---------------------------------------------------------------------------

class TestSettingsAffectCampaignFlow:
    def test_settings_affect_campaign_flow(
        self, campaign: GrandCampaignDefinition,
    ) -> None:
        # Apply HARD settings: allied=SCARCE (0.8 req mod), axis=ADEQUATE (1.0 req mod)
        hard_settings = GAME_PRESETS[GamePreset.HARD]
        applier = GameSettingsApplier(hard_settings)
        modified = applier.apply_to_campaign(campaign)

        # Axis should get more requisition than allied (relative to base)
        for sector in modified.sectors:
            for op in sector.operations:
                original_op = next(
                    o for s in campaign.sectors for o in s.operations
                    if o.operation_id == op.operation_id
                )
                # Allied gets SCARCE modifier (0.8), axis gets ADEQUATE (1.0)
                assert op.requisition_points_allies <= original_op.requisition_points_allies
                assert op.requisition_points_axis == original_op.requisition_points_axis


# ---------------------------------------------------------------------------
# 15. Supply level affects starting ammo
# ---------------------------------------------------------------------------

class TestSupplyLevelAffectsStartingAmmo:
    def test_supply_level_affects_starting_ammo(self) -> None:
        # SCARCE supply: starting_ammo_modifier = 0.75
        scarce_effects = SUPPLY_EFFECTS[SupplyLevelSetting.SCARCE]
        assert scarce_effects.starting_ammo_modifier == 0.75

        # Verify via applier on a mock unit
        settings = GameSettings(
            allied_settings=SideSettings(
                experience_level=ExperienceLevel.REGULAR,
                supply_level=SupplyLevelSetting.SCARCE,
            ),
            axis_settings=SideSettings(
                experience_level=ExperienceLevel.REGULAR,
                supply_level=SupplyLevelSetting.ADEQUATE,
            ),
        )
        applier = GameSettingsApplier(settings)

        class MockWeapon:
            max_ammo: int = 100
            ammo_remaining: int = 100

        class MockUnit:
            veterancy = None
            weapon = MockWeapon()

        unit = MockUnit()
        applier.apply_to_unit(unit, "allied")
        # SCARCE: max_ammo * 0.75 = 75
        assert unit.weapon.ammo_remaining == 75
