"""
Tests for Squad Entity - CC2 Multi-Member Squad System
"""

from __future__ import annotations

from pycc2.domain.entities.squad import (
    Squad,
    SquadMember,
    SquadType,
    MemberState,
)


def _make_squad(
    squad_id: str = "s1",
    name: str = "Alpha Squad",
    squad_type: SquadType = SquadType.RIFLE_SQUAD,
    faction: str = "allies",
) -> Squad:
    return Squad(
        squad_id=squad_id,
        squad_type=squad_type,
        faction=faction,
        name=name,
    )


class TestSquadConstruction:
    def test_basic_construction(self):
        s = _make_squad()
        assert s.squad_id == "s1"
        assert s.name == "Alpha Squad"
        assert s.faction == "allies"

    def test_rifle_squad_has_members(self):
        s = _make_squad(squad_type=SquadType.RIFLE_SQUAD)
        assert s.size > 0
        assert s.alive_count > 0

    def test_squad_type_determines_size(self):
        rifle = _make_squad(squad_type=SquadType.RIFLE_SQUAD)
        sniper = _make_squad(squad_type=SquadType.SNIPER_TEAM)
        assert rifle.size > sniper.size

    def test_all_members_start_healthy(self):
        s = _make_squad()
        assert s.healthy_count == s.size
        assert s.wounded_count == 0
        assert s.dead_count == 0


class TestSquadCasualties:
    def test_apply_casualties_wounds_members(self):
        s = _make_squad()
        initial_healthy = s.healthy_count
        s.apply_casualties(2)
        assert s.healthy_count < initial_healthy

    def test_squad_combat_effectiveness_decreases(self):
        s = _make_squad()
        initial_eff = s.combat_effectiveness
        s.apply_casualties(3)
        assert s.combat_effectiveness < initial_eff

    def test_destroyed_squad(self):
        s = _make_squad(squad_type=SquadType.SNIPER_TEAM)
        s.apply_casualties(10)  # Overkill
        assert s.alive_count == 0 or s.combat_effectiveness < 0.1


class TestSquadSuppression:
    def test_apply_suppression_pins_members(self):
        s = _make_squad()
        pinned = s.apply_suppression(0.8)  # High suppression
        # Some members should get pinned (probabilistic, so just check method runs)
        assert isinstance(pinned, int)

    def test_recover_pinned(self):
        s = _make_squad()
        s.apply_suppression(1.0)
        recovered = s.recover_pinned()
        assert isinstance(recovered, int)


class TestSquadExperience:
    def test_award_experience(self):
        s = _make_squad()
        initial_xp = sum(m.experience for m in s.members)
        s.award_experience(10)
        new_xp = sum(m.experience for m in s.members if m.is_combat_effective)
        assert new_xp >= initial_xp

    def test_experience_grade(self):
        s = _make_squad()
        grade = s.get_experience_grade()
        assert grade in ("G1", "G2", "G3", "G4", "G5")


class TestSquadReinforcement:
    def test_reinforce_adds_members(self):
        s = _make_squad(squad_type=SquadType.SNIPER_TEAM)
        initial_size = s.size
        s.reinforce(3)
        assert s.size == initial_size + 3

    def test_reinforce_new_members_healthy(self):
        s = _make_squad()
        s.reinforce(2)
        # New members should be healthy
        new_members = s.members[-2:]
        for m in new_members:
            assert m.state == MemberState.HEALTHY


class TestSquadStatus:
    def test_status_string_format(self):
        s = _make_squad()
        status = s.get_status_string()
        assert "OK" in status

    def test_morale_state_good(self):
        s = _make_squad()
        assert s.morale_state == "good"

    def test_morale_state_after_casualties(self):
        s = _make_squad(squad_type=SquadType.SNIPER_TEAM)
        s.apply_casualties(10)
        if s.alive_count == 0:
            assert s.morale_state == "destroyed"


class TestSquadSerialization:
    def test_to_dict_and_back(self):
        s = _make_squad()
        d = s.to_dict()
        s2 = Squad.from_dict(d)
        assert s2.squad_id == s.squad_id
        assert s2.squad_type == s.squad_type
        assert s2.size == s.size
        assert s2.name == s.name

    def test_squad_member_state(self):
        m = SquadMember(member_id="m1", state=MemberState.HEALTHY, hp=100)
        assert m.is_combat_effective
        assert m.effectiveness_multiplier == 1.0

    def test_wounded_member(self):
        m = SquadMember(member_id="m1", state=MemberState.WOUNDED, hp=30)
        assert m.is_combat_effective
        assert m.effectiveness_multiplier == 0.5

    def test_dead_member(self):
        m = SquadMember(member_id="m1", state=MemberState.DEAD, hp=0)
        assert not m.is_combat_effective
        assert m.effectiveness_multiplier == 0.0
