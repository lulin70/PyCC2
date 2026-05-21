from __future__ import annotations

import dataclasses
import random
from dataclasses import dataclass
from enum import Enum, auto
from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from pycc2.domain.ai.blackboard import Blackboard
    from pycc2.domain.ai.tactic_intent import TacticIntent
    from pycc2.domain.systems.game_settings import ExperienceLevel


class DifficultyLevel(Enum):
    EASY = auto()
    MEDIUM = auto()
    HARD = auto()
    VETERAN = auto()


@dataclass(slots=True)
class DifficultyConfig:
    level: DifficultyLevel

    vision_range_multiplier: float = 1.0
    reaction_delay_ticks: int = 0
    perception_accuracy: float = 1.0

    base_hit_chance: float = 0.5
    aim_time_multiplier: float = 1.0
    suppress_effectiveness: float = 1.0

    tactical_variety: float = 1.0
    retreat_threshold: float = 0.3
    aggressiveness: float = 0.5
    coordination_enabled: bool = False
    use_flanking: bool = False
    use_suppression_tactics: bool = False

    ammo_conservation: float = 1.0
    burst_size: int = 3
    burst_interval_ticks: int = 30

    morale_stability: float = 1.0
    panic_contagion_range: float = 5.0


class DifficultySystem:
    PRESETS: ClassVar[dict[DifficultyLevel, DifficultyConfig]] = {
        DifficultyLevel.EASY: DifficultyConfig(
            level=DifficultyLevel.EASY,
            vision_range_multiplier=0.7,
            reaction_delay_ticks=15,
            perception_accuracy=0.6,
            base_hit_chance=0.25,
            aim_time_multiplier=2.0,
            suppress_effectiveness=0.5,
            tactical_variety=0.8,
            retreat_threshold=0.5,
            aggressiveness=0.2,
            coordination_enabled=False,
            use_flanking=False,
            use_suppression_tactics=False,
            ammo_conservation=0.3,
            burst_size=2,
            burst_interval_ticks=60,
            morale_stability=1.5,
            panic_contagion_range=3.0,
        ),
        DifficultyLevel.MEDIUM: DifficultyConfig(
            level=DifficultyLevel.MEDIUM,
            vision_range_multiplier=1.0,
            reaction_delay_ticks=0,
            perception_accuracy=1.0,
            base_hit_chance=0.5,
            aim_time_multiplier=1.0,
            suppress_effectiveness=1.0,
            tactical_variety=1.0,
            retreat_threshold=0.3,
            aggressiveness=0.5,
            coordination_enabled=False,
            use_flanking=False,
            use_suppression_tactics=False,
            ammo_conservation=1.0,
            burst_size=3,
            burst_interval_ticks=30,
            morale_stability=1.0,
            panic_contagion_range=5.0,
        ),
        DifficultyLevel.HARD: DifficultyConfig(
            level=DifficultyLevel.HARD,
            vision_range_multiplier=1.2,
            reaction_delay_ticks=0,
            perception_accuracy=1.0,
            base_hit_chance=0.65,
            aim_time_multiplier=0.7,
            suppress_effectiveness=1.3,
            tactical_variety=0.6,
            retreat_threshold=0.2,
            aggressiveness=0.75,
            coordination_enabled=True,
            use_flanking=True,
            use_suppression_tactics=True,
            ammo_conservation=1.0,
            burst_size=4,
            burst_interval_ticks=20,
            morale_stability=0.85,
            panic_contagion_range=6.0,
        ),
        DifficultyLevel.VETERAN: DifficultyConfig(
            level=DifficultyLevel.VETERAN,
            vision_range_multiplier=1.4,
            reaction_delay_ticks=0,
            perception_accuracy=1.0,
            base_hit_chance=0.75,
            aim_time_multiplier=0.5,
            suppress_effectiveness=1.5,
            tactical_variety=0.3,
            retreat_threshold=0.15,
            aggressiveness=0.9,
            coordination_enabled=True,
            use_flanking=True,
            use_suppression_tactics=True,
            ammo_conservation=1.0,
            burst_size=5,
            burst_interval_ticks=15,
            morale_stability=0.7,
            panic_contagion_range=7.0,
        ),
    }

    def __init__(self, level: DifficultyLevel = DifficultyLevel.MEDIUM) -> None:
        preset = self.PRESETS[level]
        self._config = preset.__class__(**dataclasses.asdict(preset))
        self._level = level

    @property
    def config(self) -> DifficultyConfig:
        return self._config

    @property
    def level(self) -> DifficultyLevel:
        return self._level

    def set_level(self, level: DifficultyLevel) -> None:
        preset = self.PRESETS[level]
        self._config = preset.__class__(**dataclasses.asdict(preset))
        self._level = level

    def modify_ai_decision(
        self,
        intent: TacticIntent,
        blackboard: Blackboard,
        rng: random.Random | None = None,
    ) -> TacticIntent | None:
        if rng is None:
            rng = random.Random()

        if self._config.reaction_delay_ticks > 0:
            delay_key = f"reaction_delay_{intent.unit_id}"
            remaining = blackboard.get(delay_key, 0)
            if remaining > 0:
                blackboard.set(delay_key, remaining - 1)
                return None
            blackboard.set(delay_key, self._config.reaction_delay_ticks)

        if intent.target_unit_id and rng.random() > self._config.perception_accuracy:
            return None

        if rng.random() < (1.0 - self._config.tactical_variety):
            alternative = self._pick_alternative_tactic(intent, rng)
            if alternative is not None:
                return alternative

        if intent.tactic_type == TacticType.ATTACK:
            health_ratio = blackboard.get("health_ratio", 1.0)
            if health_ratio < self._config.retreat_threshold:
                return dataclasses.replace(
                    intent, tactic_type=TacticType.RETREAT, priority=intent.priority + 5
                )
            if rng.random() > self._config.aggressiveness:
                return dataclasses.replace(
                    intent, tactic_type=TacticType.HOLD_POSITION, priority=intent.priority + 1
                )

        ammo_ratio = blackboard.get("ammo_ratio", 1.0)
        if intent.tactic_type in (TacticType.ATTACK, TacticType.SUPPRESS_FIRE):
            if ammo_ratio < self._config.ammo_conservation and rng.random() < 0.6:
                return None

        return intent

    def _pick_alternative_tactic(
        self, intent: TacticIntent, rng: random.Random | None = None
    ) -> TacticIntent | None:
        if rng is None:
            rng = random.Random()
        alternatives: dict[TacticType, list[TacticType]] = {
            TacticType.ATTACK: [TacticType.HOLD_POSITION, TacticType.MOVE_TO],
            TacticType.MOVE_TO: [TacticType.PATROL, TacticType.DEFEND],
            TacticType.PATROL: [TacticType.IDLE, TacticType.HOLD_POSITION],
            TacticType.DEFEND: [TacticType.HOLD_POSITION, TacticType.TAKE_COVER],
        }
        alts = alternatives.get(intent.tactic_type, [])
        if not alts:
            return None
        chosen = alts[rng.randint(0, len(alts) - 1)]
        return dataclasses.replace(intent, tactic_type=chosen)

    def should_coordinate(self) -> bool:
        return self._config.coordination_enabled

    @classmethod
    def from_experience_level(cls, experience_level: ExperienceLevel) -> DifficultyConfig:
        """Create a DifficultyConfig from a GameSettings ExperienceLevel.

        Maps experience levels to difficulty presets, then applies
        experience-based modifiers on top.
        """
        from pycc2.domain.systems.game_settings import EXPERIENCE_EFFECTS, ExperienceLevel as ExpLevel

        mapping: dict[ExpLevel, DifficultyLevel] = {
            ExpLevel.CONSCRIPT: DifficultyLevel.EASY,
            ExpLevel.REGULAR: DifficultyLevel.MEDIUM,
            ExpLevel.VETERAN: DifficultyLevel.HARD,
            ExpLevel.ELITE: DifficultyLevel.VETERAN,
        }
        target_level = mapping[experience_level]
        preset = cls.PRESETS[target_level]

        exp_effects = EXPERIENCE_EFFECTS[experience_level]
        modified_base_hit = max(0.05, min(0.95, preset.base_hit_chance * exp_effects.accuracy_modifier))
        modified_morale = preset.morale_stability * exp_effects.morale_resistance

        return dataclasses.replace(
            preset,
            level=target_level,
            base_hit_chance=modified_base_hit,
            morale_stability=modified_morale,
        )

    def apply_combat_modifier(self, base_hit_chance: float) -> float:
        modified = base_hit_chance * (self._config.base_hit_chance / 0.5)
        return max(0.05, min(0.95, modified))


from pycc2.domain.ai.tactic_intent import TacticType
