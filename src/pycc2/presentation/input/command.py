"""
Game Command Data Classes

Immutable data structures representing user commands.
"""

from dataclasses import dataclass
from enum import Enum, auto


class CommandType(Enum):
    """Types of game commands."""

    MOVE = auto()
    ATTACK = auto()
    HOLD_POSITION = auto()
    DIG_IN = auto()
    SELECT_UNIT = auto()
    SELECT_GROUP = auto()
    DESELECT_ALL = auto()
    CAMERA_PAN = auto()
    CAMERA_ZOOM = auto()
    END_TURN = auto()
    TOGGLE_PAUSE = auto()
    SAVE_GAME = auto()
    LOAD_GAME = auto()
    QUIT_GAME = auto()
    DEBUG_TOGGLE = auto()
    HELP = auto()


@dataclass(frozen=True)
class GameCommand:
    """
    Immutable game command with full context.

    Attributes:
        type: Command classification
        target_position: World position for move/attack commands (optional)
        target_unit_id: Unit ID for targeted commands (optional)
        modifier_keys: Set of currently held modifier keys
        timestamp: When command was issued (for replay/debugging)
    """

    type: CommandType
    target_position: tuple[int, int] | None = None
    target_unit_id: str | None = None
    modifier_keys: frozenset = frozenset()
    timestamp: float = 0.0

    def __post_init__(self):
        """Validate command after initialization."""
        import time

        if self.timestamp == 0.0:
            object.__setattr__(self, "timestamp", time.time())

    @property
    def has_target_position(self) -> bool:
        """Check if command includes a target position."""
        return self.target_position is not None

    @property
    def has_target_unit(self) -> bool:
        """Check if command targets a specific unit."""
        return self.target_unit_id is not None

    @property
    def is_shift_held(self) -> bool:
        """Check if shift modifier is active."""
        return "shift" in self.modifier_keys

    @property
    def is_ctrl_held(self) -> bool:
        """Check if ctrl modifier is active."""
        return "ctrl" in self.modifier_keys

    @classmethod
    def create_move_command(cls, x: int, y: int, **kwargs) -> "GameCommand":
        """Factory method to create movement command."""
        return cls(type=CommandType.MOVE, target_position=(x, y), **kwargs)

    @classmethod
    def create_attack_command(
        cls, x: int, y: int, target_id: str | None = None, **kwargs
    ) -> "GameCommand":
        """Factory method to create attack command."""
        return cls(
            type=CommandType.ATTACK, target_position=(x, y), target_unit_id=target_id, **kwargs
        )

    @classmethod
    def create_select_command(cls, unit_id: str, append: bool = False, **kwargs) -> "GameCommand":
        """Factory method to create selection command."""
        modifiers = frozenset({"shift"}) if append else frozenset()
        return cls(
            type=CommandType.SELECT_UNIT, target_unit_id=unit_id, modifier_keys=modifiers, **kwargs
        )


@dataclass(frozen=True)
class CommandResult:
    """Result of command execution."""

    success: bool
    message: str = ""
    error_code: str | None = None

    @classmethod
    def ok(cls, message: str = "Success") -> "CommandResult":
        """Create successful result."""
        return cls(success=True, message=message)

    @classmethod
    def fail(cls, message: str, error_code: str | None = None) -> "CommandResult":
        """Create failed result."""
        return cls(success=False, message=message, error_code=error_code)
