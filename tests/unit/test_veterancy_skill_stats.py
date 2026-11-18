"""Unit tests for MC2-03 skill growth on ``VeterancyComponent``.

Covers the design table (docs/MC2_WAVE2_DESIGN_20261118.md §4):
- ``VeteranSkillStats`` use/success double counting via ``record_shot``
- ``hit_rate`` edge cases (no uses, mixed results)
- derived ``skill_rank`` monotonicity and the 5.0 cap
- serialization of ``skill_stats`` (to_dict / from_dict round trip)

Existing field semantics (xp/kills/shots_fired/shots_hit/rank enum) must stay
untouched — assertions below pin them.
"""

from __future__ import annotations

import pytest

from pycc2.domain.components.veterancy_component import (
    DEFAULT_SKILL,
    VeterancyComponent,
    VeteranRank,
    VeteranSkillStats,
)


@pytest.mark.unit
class TestVeteranSkillStats:
    def test_defaults_are_zero(self):
        stats = VeteranSkillStats()
        assert stats.uses == 0
        assert stats.successes == 0


@pytest.mark.unit
class TestSkillStatsDefaults:
    def test_gunnery_starts_at_zero(self):
        vc = VeterancyComponent()
        assert set(vc.skill_stats.keys()) == {"gunnery"}
        assert vc.skill_stats["gunnery"] == VeteranSkillStats()

    def test_default_skill_constant_is_gunnery(self):
        assert DEFAULT_SKILL == "gunnery"

    def test_existing_field_semantics_unchanged(self):
        vc = VeterancyComponent()
        assert vc.xp == 0
        assert vc.kills == 0
        assert vc.shots_fired == 0
        assert vc.shots_hit == 0
        assert vc.rank == VeteranRank.RECRUIT


@pytest.mark.unit
class TestRecordShotDoubleCounting:
    def test_miss_counts_use_only(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=False)
        stats = vc.skill_stats[DEFAULT_SKILL]
        assert stats.uses == 1
        assert stats.successes == 0

    def test_hit_counts_use_and_success(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=True)
        stats = vc.skill_stats[DEFAULT_SKILL]
        assert stats.uses == 1
        assert stats.successes == 1

    def test_mixed_stream_counts(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)
        vc.record_shot(hit=True)
        stats = vc.skill_stats[DEFAULT_SKILL]
        assert stats.uses == 3
        assert stats.successes == 2

    def test_legacy_shot_fields_still_updated(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=True, damage=25.0)
        vc.record_shot(hit=False)
        assert vc.shots_fired == 2
        assert vc.shots_hit == 1
        assert vc.total_damage_dealt == pytest.approx(25.0)

    def test_record_kill_keeps_original_semantics(self):
        vc = VeterancyComponent()
        rank_changed = vc.record_kill()
        assert isinstance(rank_changed, bool)
        assert vc.kills == 1
        assert vc.xp == 15


@pytest.mark.unit
class TestHitRate:
    def test_no_uses_is_zero(self):
        vc = VeterancyComponent()
        assert vc.hit_rate == 0.0

    def test_all_hits_is_one(self):
        vc = VeterancyComponent()
        for _ in range(4):
            vc.record_shot(hit=True)
        assert vc.hit_rate == pytest.approx(1.0)

    def test_partial_hits(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)
        assert vc.hit_rate == pytest.approx(0.5)

    def test_hit_rate_ignores_kills(self):
        vc = VeterancyComponent()
        vc.record_kill()
        assert vc.hit_rate == 0.0


@pytest.mark.unit
class TestSkillRank:
    def test_initial_rank_is_zero(self):
        vc = VeterancyComponent()
        assert vc.skill_rank == pytest.approx(0.0)

    def test_rank_from_kills_only(self):
        vc = VeterancyComponent()
        for _ in range(4):
            vc.record_kill()
        # 4 kills * 0.25 = 1.0, hit_rate 0.0
        assert vc.skill_rank == pytest.approx(1.0)

    def test_rank_from_hits_only(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)
        # hit_rate 0.5 * 2.0 = 1.0
        assert vc.skill_rank == pytest.approx(1.0)

    def test_rank_combined_formula(self):
        vc = VeterancyComponent()
        for _ in range(4):
            vc.record_kill()
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)
        # 4 * 0.25 + 0.5 * 2.0 = 2.0
        assert vc.skill_rank == pytest.approx(2.0)

    def test_rank_is_monotonic_under_growing_skill(self):
        vc = VeterancyComponent()
        previous = vc.skill_rank
        for _ in range(40):
            vc.record_shot(hit=True)  # hit_rate stays 1.0, uses grow
            vc.record_kill()
            assert vc.skill_rank >= previous
            previous = vc.skill_rank

    def test_rank_caps_at_five(self):
        vc = VeterancyComponent()
        for _ in range(40):
            vc.record_shot(hit=True)
        for _ in range(40):
            vc.record_kill()
        assert vc.skill_rank == pytest.approx(5.0)

    def test_rank_stays_capped_with_more_kills(self):
        vc = VeterancyComponent()
        for _ in range(100):
            vc.record_kill()
        assert vc.skill_rank == pytest.approx(5.0)

    def test_rank_does_not_touch_enum_rank(self):
        vc = VeterancyComponent()
        for _ in range(40):
            vc.record_shot(hit=True)
        for _ in range(40):
            vc.record_kill()
        assert vc.skill_rank == pytest.approx(5.0)
        assert vc.rank == VeteranRank.ELITE  # xp-driven enum tier unchanged in meaning


@pytest.mark.unit
class TestSkillStatsSerialization:
    def test_roundtrip_preserves_skill_stats(self):
        vc = VeterancyComponent()
        vc.record_shot(hit=True)
        vc.record_shot(hit=True)
        vc.record_shot(hit=False)
        restored = VeterancyComponent.from_dict(vc.to_dict())
        stats = restored.skill_stats[DEFAULT_SKILL]
        assert stats.uses == 3
        assert stats.successes == 2
        assert restored.hit_rate == pytest.approx(vc.hit_rate)
        assert restored.skill_rank == pytest.approx(vc.skill_rank)

    def test_from_dict_without_skill_stats_defaults_to_gunnery(self):
        vc = VeterancyComponent.from_dict({"xp": 100, "kills": 2})
        assert set(vc.skill_stats.keys()) == {"gunnery"}
        assert vc.skill_stats[DEFAULT_SKILL] == VeteranSkillStats()

    def test_from_dict_tolerates_malformed_skill_stats(self):
        vc = VeterancyComponent.from_dict({"skill_stats": {"gunnery": "junk", "extra": None}})
        assert vc.skill_stats[DEFAULT_SKILL] == VeteranSkillStats()

    def test_roundtrip_keeps_unknown_skills(self):
        vc = VeterancyComponent()
        vc.skill_stats["morale"] = VeteranSkillStats(uses=7, successes=3)
        restored = VeterancyComponent.from_dict(vc.to_dict())
        assert restored.skill_stats["morale"].uses == 7
        assert restored.skill_stats["morale"].successes == 3
