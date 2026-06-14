"""
Unit Tests for Campaign System (Legacy)

Tests campaign state progression, scenario loading,
mission registration, and day-based mission assignment.
"""

import pytest

from pycc2.domain.systems.campaign import (
    CampaignManager,
    MissionDefinition,
    MissionDifficulty,
    MissionObjective,
    MissionObjectiveDef,
    create_default_campaign,
)

# ===========================================================================
# Tests — MissionDefinition
# ===========================================================================


@pytest.mark.unit
class TestMissionDefinition:
    """Test MissionDefinition data class."""

    def test_basic_mission_creation(self):
        mission = MissionDefinition(
            id="m1",
            name="Test Mission",
            description="A test",
            map_id="test_map",
            difficulty=MissionDifficulty.RECRUIT,
        )
        assert mission.id == "m1"
        assert mission.player_faction == "allies"
        assert mission.is_night_mission is False
        assert mission.weather == "clear"

    def test_total_objectives_property(self):
        mission = MissionDefinition(
            id="m1",
            name="T",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.REGULAR,
            objectives=[
                MissionObjectiveDef(
                    objective_type=MissionObjective.ELIMINATE_ENEMY_FORCE,
                    description="Kill all",
                ),
                MissionObjectiveDef(
                    objective_type=MissionObjective.CAPTURE_LOCATION,
                    description="Capture",
                ),
            ],
        )
        assert mission.total_objectives == 2

    def test_empty_objectives(self):
        mission = MissionDefinition(
            id="m1",
            name="T",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.REGULAR,
        )
        assert mission.total_objectives == 0


# ===========================================================================
# Tests — CampaignManager
# ===========================================================================


@pytest.mark.unit
class TestCampaignManager:
    """Test CampaignManager mission lifecycle."""

    def test_register_and_get_mission(self):
        mgr = CampaignManager()
        mission = MissionDefinition(
            id="m1",
            name="T",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.RECRUIT,
        )
        mgr.register_mission(mission)
        assert mgr.get_mission("m1") is mission

    def test_get_nonexistent_mission(self):
        mgr = CampaignManager()
        assert mgr.get_mission("nonexistent") is None

    def test_start_mission(self):
        mgr = CampaignManager()
        mission = MissionDefinition(
            id="m1",
            name="T",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.REGULAR,
        )
        mgr.register_mission(mission)
        result = mgr.start_mission("m1")
        assert result is mission
        assert mgr._current_mission is mission

    def test_start_nonexistent_mission(self):
        mgr = CampaignManager()
        result = mgr.start_mission("nonexistent")
        assert result is None

    def test_complete_mission_victory(self):
        mgr = CampaignManager()
        mission = MissionDefinition(
            id="m1",
            name="T",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.REGULAR,
        )
        mgr.register_mission(mission)
        mgr.start_mission("m1")
        mgr.complete_current_mission(victory=True)
        assert "m1" in mgr._completed_missions
        assert mgr._current_mission is None

    def test_complete_mission_defeat(self):
        mgr = CampaignManager()
        mission = MissionDefinition(
            id="m1",
            name="T",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.REGULAR,
        )
        mgr.register_mission(mission)
        mgr.start_mission("m1")
        mgr.complete_current_mission(victory=False)
        assert "m1" not in mgr._completed_missions
        assert mgr._current_mission is None

    def test_available_missions_excludes_completed(self):
        mgr = CampaignManager()
        m1 = MissionDefinition(
            id="m1",
            name="T1",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.RECRUIT,
        )
        m2 = MissionDefinition(
            id="m2",
            name="T2",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.REGULAR,
        )
        mgr.register_mission(m1)
        mgr.register_mission(m2)
        mgr.start_mission("m1")
        mgr.complete_current_mission(victory=True)

        available = mgr.available_missions
        assert len(available) == 1
        assert available[0].id == "m2"

    def test_completed_count(self):
        mgr = CampaignManager()
        assert mgr.completed_count == 0
        m1 = MissionDefinition(
            id="m1",
            name="T1",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.RECRUIT,
        )
        mgr.register_mission(m1)
        mgr.start_mission("m1")
        mgr.complete_current_mission(victory=True)
        assert mgr.completed_count == 1

    def test_total_missions(self):
        mgr = CampaignManager()
        assert mgr.total_missions == 0
        m1 = MissionDefinition(
            id="m1",
            name="T1",
            description="D",
            map_id="m",
            difficulty=MissionDifficulty.RECRUIT,
        )
        mgr.register_mission(m1)
        assert mgr.total_missions == 1


# ===========================================================================
# Tests — Day-based Missions
# ===========================================================================


@pytest.mark.unit
class TestDayMissions:
    """Test day-based mission assignment."""

    def test_day_1_missions(self):
        mgr = create_default_campaign()
        day1 = mgr.get_missions_for_day(1)
        ids = [m.id for m in day1]
        assert "mission_01_tutorial" in ids
        assert "mission_02_bridge" in ids

    def test_day_5_missions(self):
        mgr = create_default_campaign()
        day5 = mgr.get_missions_for_day(5)
        ids = [m.id for m in day5]
        assert "mission_10_arnhem" in ids

    def test_invalid_day_returns_empty(self):
        mgr = create_default_campaign()
        missions = mgr.get_missions_for_day(99)
        assert missions == []

    def test_completed_missions_excluded_from_day(self):
        mgr = create_default_campaign()
        mgr.start_mission("mission_01_tutorial")
        mgr.complete_current_mission(victory=True)
        day1 = mgr.get_missions_for_day(1)
        ids = [m.id for m in day1]
        assert "mission_01_tutorial" not in ids


# ===========================================================================
# Tests — create_default_campaign
# ===========================================================================


@pytest.mark.unit
class TestDefaultCampaign:
    """Test the default campaign factory."""

    def test_creates_10_missions(self):
        mgr = create_default_campaign()
        assert mgr.total_missions == 10

    def test_all_missions_have_ids(self):
        mgr = create_default_campaign()
        for mid in [
            "mission_01_tutorial",
            "mission_02_bridge",
            "mission_03_hold",
            "mission_04_night",
            "mission_05_armor",
            "mission_06_son",
            "mission_07_veghel",
            "mission_08_grave",
            "mission_09_nijmegen",
            "mission_10_arnhem",
        ]:
            assert mgr.get_mission(mid) is not None

    def test_mission_difficulties_progress(self):
        mgr = create_default_campaign()
        m1 = mgr.get_mission("mission_01_tutorial")
        m5 = mgr.get_mission("mission_05_armor")
        assert m1.difficulty == MissionDifficulty.RECRUIT
        assert m5.difficulty == MissionDifficulty.HERO

    def test_night_mission_flag(self):
        mgr = create_default_campaign()
        m4 = mgr.get_mission("mission_04_night")
        assert m4.is_night_mission is True
        m1 = mgr.get_mission("mission_01_tutorial")
        assert m1.is_night_mission is False


# ===========================================================================
# Tests — Campaign State Integration
# ===========================================================================


@pytest.mark.unit
class TestCampaignStateIntegration:
    """Test campaign state mode integration."""

    def test_enable_campaign_mode(self):
        mgr = CampaignManager(use_campaign_state=False)
        assert mgr.campaign_state is None
        mgr.enable_campaign_mode()
        assert mgr.campaign_state is not None

    def test_campaign_state_on_init(self):
        mgr = CampaignManager(use_campaign_state=True)
        assert mgr.campaign_state is not None
