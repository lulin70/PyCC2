"""Animation Controller - State-based animation management for CC2 units."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

import pygame

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit
    from pycc2.presentation.rendering.direction_sprite import Direction, DirectionSpriteSet


class AnimationState(Enum):
    """Possible animation states for a unit."""
    IDLE = auto()
    MOVING = auto()
    ATTACKING = auto()
    RELOADING = auto()
    DYING = auto()
    DEAD = auto()
    SUPPRESSED = auto()
    HIDDEN = auto()


@dataclass(slots=True)
class AnimationFrame:
    """Single frame definition within an animation."""
    surface: pygame.Surface | None = None
    duration_ms: int = 100
    sprite_offset: tuple[int, int] = (0, 0)


@dataclass
class AnimationDefinition:
    """Definition of an animation sequence for one state."""
    state: AnimationState
    frames: list[AnimationFrame] = field(default_factory=list)
    loop: bool = True
    interruptible: bool = True
    on_complete: Callable[[], None] | None = None


@dataclass
class AnimationController:
    """
    Controls animation playback for a single unit.

    Features:
    - State machine: IDLE → MOVING → ATTACKING → etc.
    - Per-state frame sequences with timing
    - Smooth transitions between states
    - Direction-aware sprite selection
    - Callback hooks for animation events (death complete, reload done, etc.)
    """

    DEFAULT_FRAME_DURATION_MS: int = 150
    TRANSITION_BLEND_MS: int = 50

    def __init__(self, unit: "Unit") -> None:
        self._unit = unit
        self._current_state = AnimationState.IDLE
        self._previous_state = AnimationState.IDLE
        self._current_frame_index: int = 0
        self._state_start_time: float = 0.0
        self._frame_start_time: float = 0.0
        self._is_playing: bool = True
        self._animations: dict[AnimationState, AnimationDefinition] = {}
        self._sprite_set: DirectionSpriteSet | None = None
        self._current_direction = 0.0
        self._on_state_change: dict[
            AnimationState,
            list[Callable[[AnimationState, AnimationState], None]],
        ] = {}

        # CC2写实像素艺术系统集成
        self.use_cc2_style: bool = True  # 开关：启用新的CC2风格精灵生成器
        self._sprite_cache: dict[tuple, pygame.Surface] = {}  # 精灵缓存
        self._animation_frame: int = 0  # 当前动画帧计数

        self._initialize_default_animations()

    def _initialize_default_animations(self) -> None:
        """Set up default placeholder animations for all states."""
        placeholder_frame = AnimationFrame(duration_ms=self.DEFAULT_FRAME_DURATION_MS)

        self._animations[AnimationState.IDLE] = AnimationDefinition(
            state=AnimationState.IDLE,
            frames=[placeholder_frame, placeholder_frame],
            loop=True,
            interruptible=True,
        )

        self._animations[AnimationState.MOVING] = AnimationDefinition(
            state=AnimationState.MOVING,
            frames=[placeholder_frame] * 4,
            loop=True,
            interruptible=True,
        )

        self._animations[AnimationState.ATTACKING] = AnimationDefinition(
            state=AnimationState.ATTACKING,
            frames=[placeholder_frame] * 3,
            loop=False,
            interruptible=False,
        )

        self._animations[AnimationState.RELOADING] = AnimationDefinition(
            state=AnimationState.RELOADING,
            frames=[placeholder_frame] * 2,
            loop=False,
            interruptible=False,
        )

        self._animations[AnimationState.DYING] = AnimationDefinition(
            state=AnimationState.DYING,
            frames=[placeholder_frame] * 4,
            loop=False,
            interruptible=False,
        )

        self._animations[AnimationState.DEAD] = AnimationDefinition(
            state=AnimationState.DEAD,
            frames=[placeholder_frame],
            loop=False,
            interruptible=False,
        )

        self._animations[AnimationState.SUPPRESSED] = AnimationDefinition(
            state=AnimationState.SUPPRESSED,
            frames=[placeholder_frame] * 2,
            loop=True,
            interruptible=True,
        )

        self._animations[AnimationState.HIDDEN] = AnimationDefinition(
            state=AnimationState.HIDDEN,
            frames=[placeholder_frame],
            loop=True,
            interruptible=True,
        )

    @property
    def current_state(self) -> AnimationState:
        return self._current_state

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    def set_sprite_set(self, sprite_set: DirectionSpriteSet) -> None:
        """Assign directional sprite set for this unit."""
        self._sprite_set = sprite_set
        self._rebuild_frames_from_sprites()

    def _rebuild_frames_from_sprites(self) -> None:
        """Rebuild animation frames using actual sprite surfaces."""
        if not self._sprite_set:
            return

        from pycc2.presentation.rendering.direction_sprite import Direction

        for state, anim_def in self._animations.items():
            new_frames = []
            direction = Direction.from_angle(self._current_direction)

            for i in range(len(anim_def.frames)):
                sprite_surface = self._sprite_set.get_sprite(direction, frame_index=i)

                if sprite_surface:
                    new_frames.append(
                        AnimationFrame(
                            surface=sprite_surface,
                            duration_ms=anim_def.frames[i].duration_ms,
                        )
                    )
                else:
                    new_frames.append(anim_def.frames[i])

            anim_def.frames = new_frames

    def request_state(self, new_state: AnimationState) -> bool:
        """
        Request transition to a new animation state.

        Args:
            new_state: Target animation state

        Returns:
            True if transition accepted
        """
        if new_state == self._current_state:
            return True

        current_anim = self._animations.get(self._current_state)
        if current_anim and not current_anim.interruptible:
            is_complete = self._is_animation_complete()
            if not is_complete and self._current_state not in (
                AnimationState.DEAD,
            ):
                return False

        old_state = self._current_state
        self._previous_state = old_state
        self._current_state = new_state
        self._current_frame_index = 0
        self._state_start_time = time.perf_counter() * 1000
        self._frame_start_time = self._state_start_time

        callbacks = self._on_state_change.get(new_state, [])
        for cb in callbacks:
            try:
                cb(old_state, new_state)
            except Exception as e:
                print(f"[AnimCtrl] State change callback error: {e}")

        return True

    def update(self, delta_ms: float, current_facing: float = 0.0) -> pygame.Surface | None:
        """
        Update animation state and get current frame to render.

        Args:
            delta_ms: Time since last update in milliseconds
            current_facing: Current unit facing angle (degrees)

        Returns:
            Current frame Surface or None
        """
        if not self._is_playing:
            return self._get_current_frame_surface()

        self._current_direction = current_facing

        current_time = time.perf_counter() * 1000
        anim_def = self._animations.get(self._current_state)

        if not anim_def or not anim_def.frames:
            return None

        elapsed_since_frame = current_time - self._frame_start_time
        current_frame = anim_def.frames[self._current_frame_index]

        if elapsed_since_frame >= current_frame.duration_ms:
            self._advance_frame(anim_def)
            current_frame = anim_def.frames[self._current_frame_index]
            self._frame_start_time = current_time

        if self._current_state == AnimationState.DYING:
            if self._current_frame_index >= len(anim_def.frames) - 1:
                self.request_state(AnimationState.DEAD)

        return self._get_current_frame_surface()

    def get_frame(self, unit) -> pygame.Surface:
        """
        获取单位当前帧的精灵 - CC2写实像素艺术风格

        Args:
            unit: 单位对象（需要direction, faction, state属性）

        Returns:
            pygame.Surface: 精灵图像
        """
        if self.use_cc2_style and hasattr(unit, 'direction'):
            # 使用新的CC2写实像素生成器
            cache_key = (
                unit.unit_type.value,
                unit.faction.value if hasattr(unit, 'faction') else 'allies',
                unit.direction.value if hasattr(unit, 'direction') else 0,
                unit.state if hasattr(unit, 'state') else 'idle',
                self._animation_frame
            )

            if cache_key not in self._sprite_cache:
                try:
                    from pycc2.presentation.rendering.pixel_artist_3d import PixelArtist3D, Direction, Faction

                    direction = Direction(unit.direction.value) if hasattr(unit, 'direction') else Direction.SOUTH
                    faction = Faction(unit.faction.value.lower()) if hasattr(unit, 'faction') else Faction.ALLIES
                    state = unit.state if hasattr(unit, 'state') else 'idle'

                    sprite = PixelArtist3D.create_infantry_sprite(
                        direction=direction,
                        faction=faction,
                        state=state,
                        frame=self._animation_frame
                    )
                    self._sprite_cache[cache_key] = sprite
                    print(f"[AnimCtrl] ✅ Generated CC2 sprite: {cache_key}")
                except Exception as e:
                    print(f"[AnimCtrl] ❌ CC2 sprite generation failed: {e}, using fallback")
                    return self._get_legacy_frame(unit)

            return self._sprite_cache[cache_key]

        # 否则使用原有逻辑 (fallback)
        return self._get_legacy_frame(unit)

    def _get_legacy_frame(self, unit) -> pygame.Surface | None:
        """Fallback到原有的精灵获取逻辑"""
        return self._get_current_frame_surface()

    def _advance_frame(self, anim_def: AnimationDefinition) -> None:
        """Advance to next frame, looping if necessary."""
        next_index = self._current_frame_index + 1

        if next_index >= len(anim_def.frames):
            if anim_def.loop:
                self._current_frame_index = 0
            else:
                if anim_def.on_complete:
                    try:
                        anim_def.on_complete()
                    except Exception as e:
                        print(f"[AnimCtrl] Complete callback error: {e}")
                self._current_frame_index = min(
                    next_index, len(anim_def.frames) - 1
                )
        else:
            self._current_frame_index = next_index

    def _get_current_frame_surface(self) -> pygame.Surface | None:
        """Get the pygame Surface for the current frame."""
        anim_def = self._animations.get(self._current_state)
        if not anim_def or not anim_def.frames:
            return None

        frame = anim_def.frames[self._current_frame_index]

        if frame.surface:
            return frame.surface

        if self._sprite_set:
            from pycc2.presentation.rendering.direction_sprite import Direction
            direction = Direction.from_angle(self._current_direction)
            return self._sprite_set.get_sprite(
                direction,
                frame_index=self._current_frame_index,
            )

        return None

    def _is_animation_complete(self) -> bool:
        """Check if non-looping animation has finished."""
        anim_def = self._animations.get(self._current_state)
        if not anim_def or anim_def.loop:
            return False

        current_time = time.perf_counter() * 1000
        total_duration = sum(f.duration_ms for f in anim_def.frames)
        elapsed = current_time - self._state_start_time

        return elapsed >= total_duration

    def play(self) -> None:
        """Resume animation playback."""
        self._is_playing = True

    def pause(self) -> None:
        """Pause animation playback."""
        self._is_playing = False

    def reset(self) -> None:
        """Reset to initial idle state."""
        self._current_state = AnimationState.IDLE
        self._previous_state = AnimationState.IDLE
        self._current_frame_index = 0
        self._is_playing = True

    def register_state_change_callback(
        self,
        state: AnimationState,
        callback: Callable[[AnimationState, AnimationState], None],
    ) -> None:
        """Register callback for when entering a specific state."""
        if state not in self._on_state_change:
            self._on_state_change[state] = []
        self._on_state_change[state].append(callback)

    def force_direction(self, facing_angle: float) -> None:
        """Update unit facing without changing state."""
        self._current_direction = facing_angle
