"""
Tests for Achievement System.
"""

import tempfile

from pycc2.domain.systems.achievement_system import (
    Achievement,
    AchievementCategory,
    AchievementManager,
    AchievementRarity,
    AchievementState,
    create_default_achievements,
)


class TestAchievement:
    def test_is_complete_with_progress(self):
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=5,
        )
        assert not a.is_complete(3)
        assert a.is_complete(5)
        assert a.is_complete(10)

    def test_is_complete_single(self):
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=1,
        )
        assert not a.is_complete(0)
        assert a.is_complete(1)

    def test_get_progress_percent(self):
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=10,
        )
        assert a.get_progress_percent(0) == 0.0
        assert a.get_progress_percent(5) == 50.0
        assert a.get_progress_percent(10) == 100.0

    def test_get_progress_percent_capped(self):
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=10,
        )
        assert a.get_progress_percent(20) == 100.0


class TestAchievementState:
    def test_initial_not_unlocked(self):
        state = AchievementState(achievement_id="test")
        assert not state.is_unlocked()
        assert state.progress == 0

    def test_unlocked_with_timestamp(self):
        state = AchievementState(achievement_id="test", unlocked_at=12345.0)
        assert state.is_unlocked()


class TestAchievementManager:
    def test_register_achievement(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="first_blood",
            name="First Blood",
            description="desc",
            category=AchievementCategory.COMBAT,
        )
        mgr.register(a)
        assert not mgr.is_unlocked("first_blood")

    def test_add_progress_unlocks(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="first_blood",
            name="First Blood",
            description="desc",
            category=AchievementCategory.COMBAT,
        )
        mgr.register(a)
        unlocked = mgr.add_progress("first_blood", 1)
        assert unlocked
        assert mgr.is_unlocked("first_blood")

    def test_add_progress_incremental(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="sharpshooter",
            name="Sharpshooter",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=10,
        )
        mgr.register(a)
        assert not mgr.add_progress("sharpshooter", 5)
        assert mgr.get_progress("sharpshooter") == 5
        assert mgr.add_progress("sharpshooter", 5)
        assert mgr.is_unlocked("sharpshooter")

    def test_add_progress_already_unlocked(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
        )
        mgr.register(a)
        mgr.add_progress("test", 1)
        assert not mgr.add_progress("test", 1)

    def test_add_progress_unknown_achievement(self):
        mgr = AchievementManager()
        assert not mgr.add_progress("nonexistent", 1)

    def test_set_progress(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=10,
        )
        mgr.register(a)
        mgr.set_progress("test", 7)
        assert mgr.get_progress("test") == 7

    def test_set_progress_unlocks(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="desc",
            category=AchievementCategory.COMBAT,
            max_progress=5,
        )
        mgr.register(a)
        assert mgr.set_progress("test", 5)
        assert mgr.is_unlocked("test")

    def test_get_all_unlocked(self):
        mgr = AchievementManager()
        a1 = Achievement(
            achievement_id="a1",
            name="A1",
            description="d",
            category=AchievementCategory.COMBAT,
        )
        a2 = Achievement(
            achievement_id="a2",
            name="A2",
            description="d",
            category=AchievementCategory.CAMPAIGN,
        )
        mgr.register_many([a1, a2])
        mgr.add_progress("a1", 1)
        unlocked = mgr.get_all_unlocked()
        assert len(unlocked) == 1
        assert unlocked[0].achievement_id == "a1"

    def test_get_all_visible_hides_hidden(self):
        mgr = AchievementManager()
        a1 = Achievement(
            achievement_id="visible",
            name="Visible",
            description="d",
            category=AchievementCategory.COMBAT,
        )
        a2 = Achievement(
            achievement_id="hidden",
            name="???",
            description="d",
            category=AchievementCategory.SPECIAL,
            is_hidden=True,
        )
        mgr.register_many([a1, a2])
        visible = mgr.get_all_visible()
        visible_ids = [v[0].achievement_id for v in visible]
        assert "visible" in visible_ids
        assert "hidden" not in visible_ids

    def test_get_all_visible_shows_unlocked_hidden(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="secret",
            name="???",
            description="d",
            category=AchievementCategory.SPECIAL,
            is_hidden=True,
        )
        mgr.register(a)
        mgr.add_progress("secret", 1)
        visible = mgr.get_all_visible()
        visible_ids = [v[0].achievement_id for v in visible]
        assert "secret" in visible_ids

    def test_listener_called_on_unlock(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="d",
            category=AchievementCategory.COMBAT,
        )
        mgr.register(a)
        received = []
        mgr.add_listener(lambda ach: received.append(ach.achievement_id))
        mgr.add_progress("test", 1)
        assert len(received) == 1
        assert received[0] == "test"

    def test_listener_not_called_on_progress(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="d",
            category=AchievementCategory.COMBAT,
            max_progress=5,
        )
        mgr.register(a)
        received = []
        mgr.add_listener(lambda ach: received.append(ach.achievement_id))
        mgr.add_progress("test", 1)
        assert len(received) == 0

    def test_get_stats(self):
        mgr = AchievementManager()
        a1 = Achievement(
            achievement_id="a1",
            name="A1",
            description="d",
            category=AchievementCategory.COMBAT,
        )
        a2 = Achievement(
            achievement_id="a2",
            name="A2",
            description="d",
            category=AchievementCategory.CAMPAIGN,
        )
        mgr.register_many([a1, a2])
        mgr.add_progress("a1", 1)
        stats = mgr.get_stats()
        assert stats["total"] == 2
        assert stats["unlocked"] == 1
        assert stats["completion_pct"] == 50.0

    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr1 = AchievementManager(save_dir=tmpdir)
            a = Achievement(
                achievement_id="test",
                name="Test",
                description="d",
                category=AchievementCategory.COMBAT,
                max_progress=5,
            )
            mgr1.register(a)
            mgr1.add_progress("test", 3)
            mgr1.save()

            mgr2 = AchievementManager(save_dir=tmpdir)
            mgr2.register(a)
            mgr2.load()
            assert mgr2.get_progress("test") == 3

    def test_reset(self):
        mgr = AchievementManager()
        a = Achievement(
            achievement_id="test",
            name="Test",
            description="d",
            category=AchievementCategory.COMBAT,
        )
        mgr.register(a)
        mgr.add_progress("test", 1)
        mgr.reset()
        assert not mgr.is_unlocked("test")
        assert mgr.get_progress("test") == 0


class TestDefaultAchievements:
    def test_create_default_achievements(self):
        achievements = create_default_achievements()
        assert len(achievements) == 11

    def test_all_ids_unique(self):
        achievements = create_default_achievements()
        ids = [a.achievement_id for a in achievements]
        assert len(ids) == len(set(ids))

    def test_hidden_achievements_exist(self):
        achievements = create_default_achievements()
        hidden = [a for a in achievements if a.is_hidden]
        assert len(hidden) >= 1

    def test_categories_covered(self):
        achievements = create_default_achievements()
        categories = set(a.category for a in achievements)
        assert AchievementCategory.COMBAT in categories
        assert AchievementCategory.CAMPAIGN in categories
        assert AchievementCategory.SURVIVAL in categories
        assert AchievementCategory.SPECIAL in categories

    def test_rarities_covered(self):
        achievements = create_default_achievements()
        rarities = set(a.rarity for a in achievements)
        assert AchievementRarity.COMMON in rarities
        assert AchievementRarity.RARE in rarities

    def test_register_all_defaults(self):
        mgr = AchievementManager()
        mgr.register_many(create_default_achievements())
        stats = mgr.get_stats()
        assert stats["total"] == 11
