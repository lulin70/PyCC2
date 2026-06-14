"""CC2 Multi-Member Squad System.

Implements the core CC2 squad mechanics where each "unit" is actually a team of 3-10 soldiers:

CC2 Original Features (from screenshot analysis):
- Each visible unit = A squad of multiple soldiers
- Individual soldier states: Healthy / Wounded / Pinned / Dead / Surrendered
- Experience system: Survivors gain XP; new recruits start with difficulty-based XP
- Casualties reduce squad combat effectiveness
- Squad can operate at reduced capacity even with wounded members

Example from CC2 screenshots:
┌─────────────────────────────────────┐
│ [👤👤👤] Ness        Hide  G1    │  ← 3-man rifle squad
│ [👤👤👤👤] Robbers    Hide  G2    │  ← 4-man squad
│ [👤👤👤👤👤] Golf      Wait  G1    │  ← 5-man squad (1 pinned)
│ [👤👤]   Devotion    Hide  G3    │  ← 2-man squad (casualties!)
└─────────────────────────────────────┘

Key Mechanics:
1. Combat effectiveness scales with healthy member count
2. Pinned members cannot move/shoot but count as casualties for morale
3. Dead members are permanent loss; replaced by recruits between battles
4. Experience affects accuracy, morale recovery, and leadership
"""

import random
from dataclasses import dataclass, field
from enum import Enum

# WWII soldier name generator
_ALLIED_FIRST_NAMES = [
    "Johnson",
    "Williams",
    "Brown",
    "Jones",
    "Miller",
    "Davis",
    "Wilson",
    "Moore",
    "Taylor",
    "Anderson",
    "Thomas",
    "Jackson",
    "White",
    "Harris",
    "Martin",
    "Thompson",
    "Garcia",
    "Martinez",
    "Robinson",
    "Clark",
    "Rodriguez",
    "Lewis",
    "Lee",
    "Walker",
    "Hall",
    "Allen",
    "Young",
    "King",
    "Wright",
    "Scott",
    "Green",
    "Adams",
    "Baker",
    "Nelson",
    "Carter",
    "Mitchell",
    "Perez",
    "Roberts",
    "Turner",
    "Phillips",
    "Campbell",
    "Parker",
    "Evans",
    "Edwards",
    "Collins",
    "Stewart",
    "Sanchez",
    "Morris",
    "Rogers",
]

_AXIS_FIRST_NAMES = [
    "Müller",
    "Schmidt",
    "Schneider",
    "Fischer",
    "Weber",
    "Meyer",
    "Wagner",
    "Becker",
    "Schulz",
    "Hoffmann",
    "Koch",
    "Bauer",
    "Richter",
    "Klein",
    "Wolf",
    "Schröder",
    "Neumann",
    "Schwarz",
    "Braun",
    "Zimmermann",
    "Krüger",
    "Hartmann",
    "Lange",
    "Werner",
    "Krause",
    "Lehmann",
    "Schäfer",
    "Köhler",
    "Herrmann",
    "König",
    "Walter",
    "Mayer",
    "Huber",
    "Kaiser",
    "Fuchs",
    "Peters",
    "Lang",
    "Scholz",
    "Möller",
    "Weiß",
]

_RANKS = {
    "team_leader": ["Sgt.", "Cpl."],
    "rifleman": ["Pvt.", "Pfc."],
    "grenadier": ["Pvt.", "Pfc."],
    "mg_gunner": ["Pfc.", "Cpl."],
    "assistant_gunner": ["Pvt."],
    "sniper": ["Pfc.", "Cpl."],
    "at_gunner": ["Pfc.", "Cpl."],
    "driver": ["Pvt.", "Pfc."],
    "commander": ["Lt.", "Sgt."],
    "gunner": ["Cpl.", "Sgt."],
    "loader": ["Pvt.", "Pfc."],
    "officer": ["Lt.", "Cpt."],
    "radioman": ["Pvt.", "Pfc."],
    "runner": ["Pvt.", "Pfc."],
    "mg_assistant": ["Pvt."],
    "ammo_bearer": ["Pvt.", "Pfc."],
    "at_assistant": ["Pvt."],
    "mortar_gunner": ["Pfc.", "Cpl."],
    "spotter": ["Pvt.", "Pfc."],
    "assistant_driver": ["Pvt."],
}


class MemberState(Enum):
    """Individual soldier state in CC2."""

    HEALTHY = "healthy"  # Full combat capability
    WOUNDED = "wounded"  # Reduced capability (50% effectiveness)
    PINNED = "pinned"  # Cannot move/shoot (suppressed)
    DEAD = "dead"  # Permanent loss
    SURRENDERED = "surrendered"  # Captured (removed from squad)


@dataclass
class SquadMember:
    """Individual soldier within a CC2 squad.

    Attributes:
        member_id: Unique identifier
        state: Current combat state
        experience: XP level (0-100+)
        hp: Hit points (0-100)
        role: Specialization (rifleman/mg/AT/officer/etc.)
        name: Personal name (e.g., "Pvt. Johnson", "Cpl. Müller")
    """

    member_id: str
    state: MemberState = MemberState.HEALTHY
    experience: int = 0
    hp: int = 100
    role: str = "rifleman"
    name: str = ""

    @property
    def is_combat_effective(self) -> bool:
        """Can this soldier contribute to combat?"""
        return self.state in [MemberState.HEALTHY, MemberState.WOUNDED]

    @property
    def effectiveness_multiplier(self) -> float:
        """Combat effectiveness based on state."""
        multipliers = {
            MemberState.HEALTHY: 1.0,
            MemberState.WOUNDED: 0.5,
            MemberState.PINNED: 0.0,
            MemberState.DEAD: 0.0,
            MemberState.SURRENDERED: 0.0,
        }
        return multipliers.get(self.state, 0.0)

    def apply_damage(self, damage: int) -> bool:
        """Apply damage to this soldier. Returns True if killed."""
        self.hp -= damage
        if self.hp <= 30 and self.state == MemberState.HEALTHY:
            self.state = MemberState.WOUNDED
        elif self.hp <= 0:
            self.state = MemberState.DEAD
            self.hp = 0
            return True
        return False

    def gain_experience(self, xp: int) -> None:
        """Add experience from combat."""
        self.experience += xp
        # Experience caps at different levels based on game balance
        self.experience = min(self.experience, 200)


class SquadType(Enum):
    """Types of squads in CC2."""

    RIFLE_SQUAD = "rifle_squad"  # 9-12 men (US) / 10 men (DE)
    MG_TEAM = "mg_team"  # 4-6 men (machine gun)
    AT_TEAM = "at_team"  # 4-5 men (anti-tank)
    MORTAR_TEAM = "mortar_team"  # 4-6 men (mortar)
    SNIPER_TEAM = "sniper_team"  # 2-3 men (sniper + spotter)
    OFFICER_TEAM = "officer_team"  # 2-4 men (command)
    VEHICLE_CREW = "vehicle_crew"  # 4-5 men (tank/vehicle crew)


@dataclass
class Squad:
    """CC2 Multi-member squad - the fundamental combat unit.

    Each "unit" the player sees on screen is actually a Squad containing
    multiple SquadMember objects.

    Attributes:
        squad_id: Unique identifier
        squad_type: Type of squad (determines initial size/roles)
        faction: ALLIES or AXIS
        members: List of individual soldiers
        name: Display name (e.g., "Ness", "Robbers", "Golf")
    """

    squad_id: str
    squad_type: SquadType
    faction: str  # "allies" or "axis"
    members: list[SquadMember] = field(default_factory=list)
    name: str = ""
    total_experience_earned: int = 0  # Track cumulative XP for stats

    # === Initial size configuration (based on historical TO&E) ===
    INITIAL_SIZES = {
        SquadType.RIFLE_SQUAD: {"allies": 10, "axis": 10},
        SquadType.MG_TEAM: {"allies": 5, "axis": 5},
        SquadType.AT_TEAM: {"allies": 4, "axis": 4},
        SquadType.MORTAR_TEAM: {"allies": 5, "axis": 5},
        SquadType.SNIPER_TEAM: {"allies": 2, "axis": 2},
        SquadType.OFFICER_TEAM: {"allies": 3, "axis": 3},
        SquadType.VEHICLE_CREW: {"allies": 5, "axis": 5},
    }

    def __post_init__(self):
        """Initialize squad with default members if empty."""
        if not self.members:
            self._initialize_members()

    def _initialize_members(self, difficulty: str = "normal") -> None:
        """Create initial squad members based on type and difficulty.

        Difficulty affects starting experience:
        - easy: 20-40 XP per member
        - normal: 10-25 XP per member
        - hard: 0-15 XP per member
        - veteran: 30-50 XP per member
        """
        base_size = self.INITIAL_SIZES.get(self.squad_type, {"allies": 8, "axis": 8}).get(
            self.faction, 8
        )

        # XP range based on difficulty
        xp_ranges = {
            "easy": (20, 40),
            "normal": (10, 25),
            "hard": (0, 15),
            "veteran": (30, 50),
        }
        xp_min, xp_max = xp_ranges.get(difficulty, (10, 25))

        # Role distribution based on squad type
        roles = self._get_role_distribution()

        for i in range(base_size):
            role = roles[i % len(roles)] if roles else "rifleman"
            member = SquadMember(
                member_id=f"{self.squad_id}_m{i}",
                state=MemberState.HEALTHY,
                experience=random.randint(xp_min, xp_max),
                hp=100,
                role=role,
                name=self._generate_soldier_name(role),
            )
            self.members.append(member)

        # Generate random name if not set
        if not self.name:
            self.name = self._generate_random_name()

    def _get_role_distribution(self) -> list[str]:
        """Get role distribution for this squad type."""
        role_maps = {
            SquadType.RIFLE_SQUAD: [
                "rifleman",
                "rifleman",
                "rifleman",
                "rifleman",
                "grenadier",
                "team_leader",
            ],
            SquadType.MG_TEAM: [
                "mg_gunner",
                "mg_assistant",
                "ammo_bearer",
                "rifleman",
                "team_leader",
            ],
            SquadType.AT_TEAM: ["at_gunner", "at_assistant", "rifleman", "rifleman", "team_leader"],
            SquadType.MORTAR_TEAM: [
                "mortar_gunner",
                "ammo_bearer",
                "rifleman",
                "rifleman",
                "team_leader",
            ],
            SquadType.SNIPER_TEAM: ["sniper", "spotter"],
            SquadType.OFFICER_TEAM: ["officer", "radioman", "runner"],
            SquadType.VEHICLE_CREW: ["commander", "gunner", "loader", "driver", "assistant_driver"],
        }
        return role_maps.get(self.squad_type, ["rifleman"])

    def _generate_random_name(self) -> str:
        """Generate a random squad name (like CC2's "Ness", "Robbers")."""
        prefixes = [
            "Alpha",
            "Bravo",
            "Charlie",
            "Delta",
            "Echo",
            "Ness",
            "Robbers",
            "Golf",
            "Devotion",
            "Vengeance",
            "Iron",
            "Steel",
            "Thunder",
            "Lightning",
            "Storm",
        ]
        suffixes = ["", " One", " Two", " Prime", " Squad", " Team", " Element", " Section"]
        return random.choice(prefixes) + random.choice(suffixes)

    def _generate_soldier_name(self, role: str) -> str:
        """Generate a personal name for a soldier based on faction and role.

        Returns a name like "Pvt. Johnson" (Allies) or "Gefr. Müller" (Axis).
        """
        if self.faction == "axis":
            surname = random.choice(_AXIS_FIRST_NAMES)
        else:
            surname = random.choice(_ALLIED_FIRST_NAMES)

        rank_options = _RANKS.get(role, ["Pvt."])
        rank = random.choice(rank_options)
        return f"{rank} {surname}"

    # === Combat Status Queries ===

    @property
    def size(self) -> int:
        """Total number of members (including dead)."""
        return len(self.members)

    @property
    def alive_count(self) -> int:
        """Number of living members (healthy + wounded)."""
        return sum(1 for m in self.members if m.state in [MemberState.HEALTHY, MemberState.WOUNDED])

    @property
    def healthy_count(self) -> int:
        """Number of fully effective members."""
        return sum(1 for m in self.members if m.state == MemberState.HEALTHY)

    @property
    def wounded_count(self) -> int:
        """Number of wounded members."""
        return sum(1 for m in self.members if m.state == MemberState.WOUNDED)

    @property
    def dead_count(self) -> int:
        """Number of dead members."""
        return sum(1 for m in self.members if m.state == MemberState.DEAD)

    @property
    def pinned_count(self) -> int:
        """Number of pinned members."""
        return sum(1 for m in self.members if m.state == MemberState.PINNED)

    @property
    def combat_effectiveness(self) -> float:
        """Overall combat effectiveness (0.0 to 1.0).

        Calculated as weighted average of all living members.
        Dead/pinned members contribute 0.
        Wounded members contribute 50%.
        """
        if not self.members:
            return 0.0
        total = sum(m.effectiveness_multiplier for m in self.members)
        return total / len(self.members)

    @property
    def is_destroyed(self) -> bool:
        """Squad is destroyed if all members are dead/surrendered."""
        return self.alive_count == 0

    @property
    def is_combat_capable(self) -> bool:
        """Squad can still fight if any healthy/wounded members remain."""
        return self.alive_count > 0

    @property
    def morale_state(self) -> str:
        """Morale state based on casualty ratio."""
        if self.is_destroyed:
            return "destroyed"
        ratio = self.alive_count / self.size
        if ratio > 0.8:
            return "good"  # < 20% casualties
        elif ratio > 0.5:
            return "shaken"  # 20-50% casualties
        elif ratio > 0.25:
            return "broken"  # 50-75% casualties
        else:
            return "routing"  # > 75% casualties

    # === Combat Actions ===

    def apply_casualties(self, num_casualties: int) -> list[SquadMember]:
        """Apply casualties to squad. Returns list of newly dead members."""
        newly_dead = []
        remaining = num_casualties

        # First pass: wound healthy members
        healthy = [m for m in self.members if m.state == MemberState.HEALTHY]
        for member in healthy:
            if remaining <= 0:
                break
            member.state = MemberState.WOUNDED
            member.hp = 35  # Wounded threshold
            remaining -= 1

        # Second pass: kill wounded members if casualties exceed healthy count
        wounded = [m for m in self.members if m.state == MemberState.WOUNDED]
        for member in wounded:
            if remaining <= 0:
                break
            member.state = MemberState.DEAD
            member.hp = 0
            newly_dead.append(member)
            remaining -= 1

        return newly_dead

    def apply_suppression(self, suppression_level: float) -> int:
        """Apply suppression. Returns number of newly pinned members.

        Higher suppression_level → more members get pinned.
        """
        newly_pinned = 0
        for member in self.members:
            if member.state == MemberState.HEALTHY:
                if random.random() < suppression_level * 0.7:
                    member.state = MemberState.PINNED
                    newly_pinned += 1
        return newly_pinned

    def recover_pinned(self) -> int:
        """Attempt to recover pinned members. Returns number recovered."""
        recovered = 0
        for member in self.members:
            if member.state == MemberState.PINNED:
                # Recovery chance based on experience
                recovery_chance = 0.3 + (member.experience / 200) * 0.4
                if random.random() < recovery_chance:
                    member.state = MemberState.HEALTHY
                    recovered += 1
        return recovered

    def award_experience(self, xp_per_member: int = 5) -> None:
        """Award experience to all surviving members."""
        for member in self.members:
            if member.is_combat_effective:
                old_xp = member.experience
                member.gain_experience(xp_per_member)
                self.total_experience_earned += member.experience - old_xp

    # === Reinforcement (Between Battles) ===

    def reinforce(self, num_reinforcements: int, difficulty: str = "normal") -> None:
        """Add new replacement members to squad.

        New recruits start with difficulty-based initial XP:
        - easy: 20-40 XP
        - normal: 10-25 XP
        - hard: 0-15 XP
        """
        xp_ranges = {
            "easy": (20, 40),
            "normal": (10, 25),
            "hard": (0, 15),
            "veteran": (30, 50),
        }
        xp_min, xp_max = xp_ranges.get(difficulty, (10, 25))
        roles = self._get_role_distribution()

        for _i in range(num_reinforcements):
            role = roles[len(self.members) % len(roles)] if roles else "rifleman"
            new_member = SquadMember(
                member_id=f"{self.squad_id}_reinforce_{len(self.members)}",
                state=MemberState.HEALTHY,
                experience=random.randint(xp_min, xp_max),
                hp=100,
                role=role,
                name=self._generate_soldier_name(role),
            )
            self.members.append(new_member)

    def remove_dead(self) -> list[SquadMember]:
        """Remove all dead members from squad. Returns removed list."""
        dead = [m for m in self.members if m.state == MemberState.DEAD]
        self.members = [m for m in self.members if m.state != MemberState.DEAD]
        return dead

    # === Serialization ===

    def to_dict(self) -> dict:
        """Convert squad to dictionary for serialization."""
        return {
            "squad_id": self.squad_id,
            "squad_type": self.squad_type.value,
            "faction": self.faction,
            "name": self.name,
            "members": [
                {
                    "member_id": m.member_id,
                    "state": m.state.value,
                    "experience": m.experience,
                    "hp": m.hp,
                    "role": m.role,
                    "name": m.name,
                }
                for m in self.members
            ],
            "total_experience_earned": self.total_experience_earned,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Squad":
        """Recreate squad from dictionary."""
        squad = cls(
            squad_id=data["squad_id"],
            squad_type=SquadType(data["squad_type"]),
            faction=data["faction"],
            name=data.get("name", ""),
            total_experience_earned=data.get("total_experience_earned", 0),
        )
        squad.members = [
            SquadMember(
                member_id=m["member_id"],
                state=MemberState(m["state"]),
                experience=m["experience"],
                hp=m["hp"],
                role=m["role"],
                name=m.get("name", ""),
            )
            for m in data["members"]
        ]
        return squad

    # === Display Helpers ===

    def get_status_string(self) -> str:
        """Get human-readable status string (for UI display).

        Format: "Healthy/Wounded/Pinned/Dead" like CC2.
        """
        parts = []
        if self.healthy_count > 0:
            parts.append(f"{self.healthy_count} OK")
        if self.wounded_count > 0:
            parts.append(f"{self.wounded_count} Wnd")
        if self.pinned_count > 0:
            parts.append(f"{self.pinned_count} Pin")
        if self.dead_count > 0:
            parts.append(f"{self.dead_count} Dead")
        return " | ".join(parts) if parts else "Destroyed"

    def get_experience_grade(self) -> str:
        """Get experience grade letter (G1-G5 like CC2)."""
        avg_exp = sum(m.experience for m in self.members if m.is_combat_effective) / max(
            1, self.alive_count
        )
        if avg_exp >= 80:
            return "G5"
        elif avg_exp >= 60:
            return "G4"
        elif avg_exp >= 40:
            return "G3"
        elif avg_exp >= 20:
            return "G2"
        else:
            return "G1"

    def __repr__(self) -> str:
        return (
            f"Squad({self.name}, {self.squad_type.value}, "
            f"{self.alive_count}/{self.size} alive, "
            f"eff={self.combat_effectiveness:.0%})"
        )
