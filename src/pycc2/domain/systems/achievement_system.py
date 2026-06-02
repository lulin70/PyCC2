"""
Achievement System - Track and reward player accomplishments.

Provides:
- Achievement definitions (hidden/revealed/progress-based)
- AchievementManager for tracking progress and unlocks
- Persistence via JSON storage (local)
- Event hooks for game systems to trigger checks

Achievement categories:
1. COMBAT - Kill-related achievements
2. CAMPAIGN - Progress milestones
3. SURVIVAL - Survival challenges
4. SPECIAL - Hidden/easter egg achievements
"""

from enum import Enum, auto
from dataclasses import dataclass, field
import json
import os
import time
from typing import Any, Callable, Dict, List, Optional, Set


class AchievementCategory(Enum):
    COMBAT = "combat"
    CAMPAIGN = "campaign"
    SURVIVAL = "survival"
    SPECIAL = "special"


class AchievementRarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"


@dataclass
class Achievement:
    """Single achievement definition."""
    achievement_id: str
    name: str
    description: str
    category: AchievementCategory
    rarity: AchievementRarity = AchievementRarity.COMMON
    is_hidden: bool = False
    max_progress: int = 1
    icon_key: str = ""
    unlock_condition: str = ""

    def is_complete(self, current_progress: int) -> bool:
        return current_progress >= self.max_progress

    def get_progress_percent(self, current_progress: int) -> float:
        if self.max_progress <= 0:
            return 100.0
        return min(100.0, (current_progress / self.max_progress) * 100)


@dataclass
class AchievementState:
    """Runtime state for a single achievement."""
    achievement_id: str
    progress: int = 0
    unlocked_at: Optional[float] = None
    notified: bool = False

    def is_unlocked(self) -> bool:
        return self.unlocked_at is not None


class AchievementManager:
    """Central manager for achievement tracking, unlocking, and persistence."""

    SAVE_DIR = "saves"
    ACHIEVEMENTS_FILE = "achievements.json"

    def __init__(self, save_dir: Optional[str] = None):
        self._definitions: Dict[str, Achievement] = {}
        self._states: Dict[str, AchievementState] = {}
        self._listeners: List[Callable[[Achievement], None]] = []
        self._save_dir = save_dir or self.SAVE_DIR
        self._loaded = False

    def register(self, achievement: Achievement) -> None:
        """Register an achievement definition."""
        self._definitions[achievement.achievement_id] = achievement
        if achievement.achievement_id not in self._states:
            self._states[achievement.achievement_id] = AchievementState(
                achievement_id=achievement.achievement_id
            )

    def register_many(self, achievements: List[Achievement]) -> None:
        for a in achievements:
            self.register(a)

    def add_listener(self, callback: Callable[[Achievement], None]) -> None:
        """Add callback triggered when achievement is unlocked."""
        self._listeners.append(callback)

    def add_progress(self, achievement_id: str, amount: int = 1) -> bool:
        """Add progress toward an achievement. Returns True if just unlocked."""
        if achievement_id not in self._definitions:
            return False

        state = self._states.get(achievement_id)
        if state is None:
            state = AchievementState(achievement_id=achievement_id)
            self._states[achievement_id] = state

        if state.is_unlocked():
            return False

        definition = self._definitions[achievement_id]
        state.progress = min(state.progress + amount, definition.max_progress)

        if definition.is_complete(state.progress):
            state.unlocked_at = time.time()
            for listener in self._listeners:
                try:
                    listener(definition)
                except Exception:
                    pass
            return True

        return False

    def set_progress(self, achievement_id: str, value: int) -> bool:
        """Set absolute progress. Returns True if just unlocked."""
        if achievement_id not in self._definitions:
            return False

        state = self._states.get(achievement_id)
        if state is None:
            state = AchievementState(achievement_id=achievement_id)
            self._states[achievement_id] = state

        if state.is_unlocked():
            return False

        definition = self._definitions[achievement_id]
        state.progress = min(value, definition.max_progress)

        if definition.is_complete(state.progress):
            state.unlocked_at = time.time()
            for listener in self._listeners:
                try:
                    listener(definition)
                except Exception:
                    pass
            return True

        return False

    def is_unlocked(self, achievement_id: str) -> bool:
        state = self._states.get(achievement_id)
        return state.is_unlocked() if state else False

    def get_progress(self, achievement_id: str) -> int:
        state = self._states.get(achievement_id)
        return state.progress if state else 0

    def get_all_unlocked(self) -> List[Achievement]:
        result = []
        for aid, state in self._states.items():
            if state.is_unlocked() and aid in self._definitions:
                result.append(self._definitions[aid])
        return result

    def get_all_visible(self) -> List[tuple]:
        """Return (Achievement, progress, is_unlocked) for non-hidden items."""
        result = []
        for aid, definition in self._definitions.items():
            if definition.is_hidden:
                state = self._states.get(aid)
                if state and state.is_unlocked():
                    result.append((definition, state.progress, True))
            else:
                state = self._states.get(aid)
                progress = state.progress if state else 0
                unlocked = state.is_unlocked() if state else False
                result.append((definition, progress, unlocked))
        return result

    def get_stats(self) -> Dict[str, Any]:
        total = len(self._definitions)
        unlocked = sum(1 for s in self._states.values() if s.is_unlocked())
        by_category: Dict[str, int] = {}
        for aid, state in self._states.items():
            if state.is_unlocked() and aid in self._definitions:
                cat = self._definitions[aid].category.value
                by_category[cat] = by_category.get(cat, 0) + 1
        return {
            "total": total,
            "unlocked": unlocked,
            "completion_pct": (unlocked / total * 100) if total > 0 else 0,
            "by_category": by_category,
        }

    def save(self) -> bool:
        """Persist achievement states to JSON file."""
        try:
            os.makedirs(self._save_dir, exist_ok=True)
            filepath = os.path.join(self._save_dir, self.ACHIEVEMENTS_FILE)
            data = {}
            for aid, state in self._states.items():
                data[aid] = {
                    "progress": state.progress,
                    "unlocked_at": state.unlocked_at,
                    "notified": state.notified,
                }
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except (OSError, json.JSONEncodeError):
            return False

    def load(self) -> bool:
        """Load achievement states from JSON file."""
        try:
            filepath = os.path.join(self._save_dir, self.ACHIEVEMENTS_FILE)
            if not os.path.exists(filepath):
                self._loaded = True
                return True
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            for aid, state_data in data.items():
                self._states[aid] = AchievementState(
                    achievement_id=aid,
                    progress=state_data.get("progress", 0),
                    unlocked_at=state_data.get("unlocked_at"),
                    notified=state_data.get("notified", False),
                )
            self._loaded = True
            return True
        except (OSError, json.JSONDecodeError):
            self._loaded = True
            return False

    def reset(self) -> None:
        """Reset all achievement progress (for testing)."""
        for state in self._states.values():
            state.progress = 0
            state.unlocked_at = None
            state.notified = False


def create_default_achievements() -> List[Achievement]:
    """Create the default set of PyCC2 achievements."""
    return [
        Achievement(
            achievement_id="first_blood",
            name="First Blood",
            description="Eliminate your first enemy unit",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.COMMON,
        ),
        Achievement(
            achievement_id="sharpshooter",
            name="Sharpshooter",
            description="Achieve 10 kills with sniper units",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.UNCOMMON,
            max_progress=10,
        ),
        Achievement(
            achievement_id="tank_buster",
            name="Tank Buster",
            description="Destroy 5 enemy tanks",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.RARE,
            max_progress=5,
        ),
        Achievement(
            achievement_id="zero_casualties",
            name="Zero Casualties",
            description="Complete a battle without losing any units",
            category=AchievementCategory.SURVIVAL,
            rarity=AchievementRarity.EPIC,
        ),
        Achievement(
            achievement_id="blitzkrieg",
            name="Blitzkrieg",
            description="Win a battle in under 2 minutes",
            category=AchievementCategory.COMBAT,
            rarity=AchievementRarity.RARE,
        ),
        Achievement(
            achievement_id="market_garden",
            name="Operation Market Garden",
            description="Complete the full Market Garden campaign",
            category=AchievementCategory.CAMPAIGN,
            rarity=AchievementRarity.EPIC,
        ),
        Achievement(
            achievement_id="bridge_too_far",
            name="A Bridge Too Far",
            description="Hold Arnhem bridge for 10 turns",
            category=AchievementCategory.CAMPAIGN,
            rarity=AchievementRarity.LEGENDARY,
            max_progress=10,
        ),
        Achievement(
            achievement_id="survivor",
            name="Survivor",
            description="Win 5 battles with at least one unit at critical health",
            category=AchievementCategory.SURVIVAL,
            rarity=AchievementRarity.UNCOMMON,
            max_progress=5,
        ),
        Achievement(
            achievement_id="commander",
            name="Supreme Commander",
            description="Win 25 battles total",
            category=AchievementCategory.CAMPAIGN,
            rarity=AchievementRarity.EPIC,
            max_progress=25,
        ),
        Achievement(
            achievement_id="flawless",
            name="Flawless Victory",
            description="Win 3 consecutive battles without any unit taking damage",
            category=AchievementCategory.SURVIVAL,
            rarity=AchievementRarity.LEGENDARY,
            max_progress=3,
        ),
        Achievement(
            achievement_id="hidden_tribute",
            name="???",
            description="A tribute to the original Close Combat 2 developers",
            category=AchievementCategory.SPECIAL,
            rarity=AchievementRarity.LEGENDARY,
            is_hidden=True,
        ),
    ]
