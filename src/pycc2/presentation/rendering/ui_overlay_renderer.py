"""UI Overlay Renderer Sub-Module for CC2-Style Games

Handles all UI overlay rendering on top of the game world:
- Victory Location flags and edge arrows (with VP pulse animation)
- Attack lines (CC2-style color-coded: green/red/orange)
- Queued command lines (Shift+right-click waypoints)
- Line-of-Sight overlay (Ctrl-key visibility visualization)

Dependencies are injected via RenderContext + optional attack_line_system.
"""

from __future__ import annotations

import logging
import math
import time as _time
from typing import TYPE_CHECKING

import pygame

from pycc2.domain.value_objects.vec2 import Vec2
from pycc2.presentation.rendering.render_context import RenderContext
from pycc2.presentation.rendering.rendering_utils import draw_dashed_line

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from pycc2.domain.entities.game_map import GameMap
    from pycc2.presentation.rendering.camera import Camera


class UIOverlayRenderer:
    """Handles all UI overlay rendering operations.

    Manages:
    - Victory Location flags with animated VP numbers
    - Edge arrows for off-screen objectives
    - Color-coded attack lines (CC2-style)
    - Queued command waypoints (dashed lines)
    - LOS visualization overlay
    """

    # Pulse animation constants for VP number display
    PULSE_BASE_ALPHA = 200
    PULSE_AMPLITUDE = 55
    PULSE_FREQUENCY = 2.0

    def __init__(self, ctx: RenderContext):
        """Initialize the UIOverlayRenderer."""
        self._ctx = ctx
        self._attack_line_system = None
        self._los_overlay: pygame.Surface | None = None
        self._los_overlay_size: tuple[int, int] = (0, 0)

    def set_attack_line_system(self, attack_line_system) -> None:
        """Set attack line system (dependency injection)."""
        self._attack_line_system = attack_line_system

    # ------------------------------------------------------------------ #
    #  Victory Location Flags
    # ------------------------------------------------------------------ #

    def draw_vl_flags(self, game_map: GameMap, camera: Camera) -> None:
        """Draw Victory Location flags and edge arrows on the map.

        Delegates to SpriteRenderer if available, otherwise draws directly.
        """
        if self._ctx.offscreen is None:
            return

        # Delegate to SpriteRenderer which has the VL flag drawing methods
        if self._ctx.sprite_renderer is not None:
            original_target = self._ctx.sprite_renderer._target_surface
            self._ctx.sprite_renderer._target_surface = self._ctx.offscreen
            try:
                self._ctx.sprite_renderer._draw_vl_flags(game_map, camera)
            finally:
                self._ctx.sprite_renderer._target_surface = original_target
            return

        # Fallback: simple direct drawing if no SpriteRenderer
        self._draw_vl_flags_fallback(game_map, camera)

    def _draw_vl_flags_fallback(self, game_map: GameMap, camera: Camera) -> None:
        """Direct drawing fallback when SpriteRenderer is unavailable."""
        offscreen = self._ctx.offscreen
        if offscreen is None:
            return
        tile_size = self._ctx.tile_size

        objectives = getattr(game_map, "objectives", [])
        if not objectives:
            return

        screen_w = offscreen.get_width()
        screen_h = offscreen.get_height()
        off_screen_vls: list[tuple[int, int, str]] = []

        for obj in objectives:
            tile_x = obj.position.x * tile_size + tile_size // 2
            tile_y = obj.position.y * tile_size + tile_size // 2
            sp = camera.world_to_screen(Vec2(tile_x, tile_y))
            sx, sy = int(sp[0]), int(sp[1])

            owner = getattr(obj, "owner", None) or "neutral"
            margin = 60
            on_screen = -margin < sx < screen_w + margin and -margin < sy < screen_h + margin

            if on_screen:
                # Simple flag drawing
                pygame.draw.line(offscreen, (80, 80, 80), (sx, sy), (sx, sy - 20), 2)
                if owner == "allies":
                    flag_color = (60, 100, 200)
                elif owner == "axis":
                    flag_color = (200, 60, 60)
                else:
                    flag_color = (200, 200, 200)
                flag_points = [
                    (sx + 1, sy - 20),
                    (sx + 14, sy - 17),
                    (sx + 13, sy - 10),
                    (sx + 1, sy - 13),
                ]
                pygame.draw.polygon(offscreen, flag_color, flag_points)
                pygame.draw.polygon(offscreen, (0, 0, 0), flag_points, 1)

                # VP number with pulse animation (yellow + shadow outline + scale)
                vp_value = getattr(obj, "points", None)
                if vp_value is not None and isinstance(vp_value, (int, float)):
                    try:
                        font = pygame.font.Font(None, 38)
                        vp_text = str(int(vp_value))

                        pulse_scale = math.sin(_time.time() * 3.0) * 0.05 + 1.0
                        pulse_alpha = int(
                            self.PULSE_BASE_ALPHA
                            + self.PULSE_AMPLITUDE
                            * abs(math.sin(_time.time() * self.PULSE_FREQUENCY))
                        )

                        text_color = (255, 220, 100)

                        base_x = sx - font.size(vp_text)[0] // 2
                        base_y = sy - 40

                        # Black outline (4-direction 1px offset)
                        for dx, dy in [(-1, -1), (1, -1), (-1, 1), (1, 1)]:
                            outline_surf = font.render(vp_text, True, (0, 0, 0))
                            outline_surf.set_alpha(pulse_alpha)
                            offset_x = int(base_x + dx * pulse_scale)
                            offset_y = int(base_y + dy * pulse_scale)
                            offscreen.blit(outline_surf, (offset_x, offset_y))

                        # Main text (bright gold + scale animation)
                        text_surf = font.render(vp_text, True, text_color)
                        text_surf.set_alpha(pulse_alpha)

                        if pulse_scale != 1.0:
                            new_w = int(text_surf.get_width() * pulse_scale)
                            new_h = int(text_surf.get_height() * pulse_scale)
                            text_surf = pygame.transform.scale(text_surf, (new_w, new_h))

                        final_x = int(base_x - (text_surf.get_width() - font.size(vp_text)[0]) // 2)
                        final_y = int(
                            base_y - (text_surf.get_height() - font.size(vp_text)[1]) // 2
                        )
                        offscreen.blit(text_surf, (final_x, final_y))
                    except (AttributeError, ValueError):
                        pass
            else:
                off_screen_vls.append((tile_x, tile_y, owner))

        # Edge arrows for off-screen VLs
        self._draw_edge_arrows(off_screen_vls, screen_w, screen_h, camera)

    def _draw_edge_arrows(
        self,
        off_screen_vls: list[tuple[int, int, str]],
        screen_w: int,
        screen_h: int,
        camera: Camera,
    ) -> None:
        """Draw directional arrows at screen edges pointing to off-screen VLs."""
        offscreen = self._ctx.offscreen
        if offscreen is None:
            return
        arrow_margin = 30

        for wx, wy, owner in off_screen_vls:
            sp = camera.world_to_screen(Vec2(wx, wy))
            sx, sy = sp[0], sp[1]
            cx = max(arrow_margin, min(screen_w - arrow_margin, sx))
            cy = max(arrow_margin, min(screen_h - arrow_margin, sy))
            color = (
                (60, 100, 200)
                if owner == "allies"
                else (200, 60, 60)
                if owner == "axis"
                else (200, 200, 200)
            )
            angle = math.atan2(sy - cy, sx - cx)
            arrow_size = 10
            tip_x = cx + arrow_size * math.cos(angle)
            tip_y = cy + arrow_size * math.sin(angle)
            left_x = cx + arrow_size * math.cos(angle + 2.5)
            left_y = cy + arrow_size * math.sin(angle + 2.5)
            right_x = cx + arrow_size * math.cos(angle - 2.5)
            right_y = cy + arrow_size * math.sin(angle - 2.5)
            pygame.draw.polygon(
                offscreen,
                color,
                [
                    (int(tip_x), int(tip_y)),
                    (int(left_x), int(left_y)),
                    (int(right_x), int(right_y)),
                ],
            )

    # ------------------------------------------------------------------ #
    #  Attack Lines
    # ------------------------------------------------------------------ #

    def draw_attack_lines(self, camera: Camera) -> None:
        """Draw CC2-style attack lines with color coding.

        Green line = Can attack (in range, clear LOS)
        Red/Orange line = Cannot attack (out of range or blocked)
        Yellow dashed = Tracking unit target
        """
        if self._ctx.offscreen is None:
            return

        attack_line = self._attack_line_system
        if not attack_line:
            return

        import pygame as pg

        from pycc2.presentation.input.attack_line_system import AttackLineStatus

        offscreen = self._ctx.offscreen

        # Draw active attack line (while in ATTACK mode)
        if attack_line.state.active and attack_line.state.source_position:
            source = attack_line.state.source_position
            target_state = attack_line.state.target

            if target_state:
                src_screen = camera.world_to_screen(source)
                tgt_screen = camera.world_to_screen(target_state.position)

                status = target_state.status
                color = attack_line.get_line_color(status)

                start_pos = (int(src_screen[0]), int(src_screen[1]))
                end_pos = (int(tgt_screen[0]), int(tgt_screen[1]))

                if status == AttackLineStatus.CAN_ATTACK:
                    pg.draw.line(offscreen, color[:3], start_pos, end_pos, 2)
                    pg.draw.circle(offscreen, (0, 255, 0), end_pos, 6, 2)
                elif status == AttackLineStatus.OUT_OF_RANGE:
                    self._draw_dashed_line(start_pos, end_pos, (255, 50, 50), dash_len=8)
                    size = 6
                    pg.draw.line(
                        offscreen,
                        (255, 50, 50),
                        (end_pos[0] - size, end_pos[1] - size),
                        (end_pos[0] + size, end_pos[1] + size),
                        2,
                    )
                    pg.draw.line(
                        offscreen,
                        (255, 50, 50),
                        (end_pos[0] - size, end_pos[1] + size),
                        (end_pos[0] + size, end_pos[1] - size),
                        2,
                    )
                elif status == AttackLineStatus.BLOCKED:
                    self._draw_dashed_line(start_pos, end_pos, (255, 140, 0), dash_len=8)
                    pg.draw.circle(offscreen, (255, 140, 0), end_pos, 8, 2)
                    pg.draw.line(
                        offscreen,
                        (255, 140, 0),
                        (end_pos[0] - 4, end_pos[1]),
                        (end_pos[0] + 4, end_pos[1]),
                        2,
                    )

        # Draw confirmed attacks (tracking lines)
        for _unit_id, confirmed_target in attack_line._confirmed_attacks.items():
            if not confirmed_target.unit_id:
                continue

            source_pos = getattr(attack_line, "_active_source", None)
            if source_pos is not None:
                source_screen = camera.world_to_screen(source_pos)
            else:
                source_screen = camera.world_to_screen(confirmed_target.position)
            target_screen = camera.world_to_screen(confirmed_target.position)

            pg.draw.line(
                offscreen,
                (255, 50, 50),
                (int(source_screen[0]), int(source_screen[1])),
                (int(target_screen[0]), int(target_screen[1])),
                2,
            )

    # ------------------------------------------------------------------ #
    #  Queued Commands
    # ------------------------------------------------------------------ #

    def draw_queued_commands(self, units: list, camera: Camera) -> None:
        """Draw dashed lines for queued commands (Shift+right-click).

        Cyan dashed lines show queued move waypoints.
        Orange dashed lines show queued attack targets.
        Each waypoint is numbered (1, 2, 3...) to indicate execution order,
        matching CC2 original command-queue visualization.
        """
        if self._ctx.offscreen is None:
            return

        offscreen = self._ctx.offscreen

        for unit in units:
            if not hasattr(unit, "has_queued_commands") or not unit.has_queued_commands:
                continue

            upos = (
                unit.position.pixel_position if hasattr(unit.position, "pixel_position") else None
            )
            if upos is None:
                continue

            prev_screen = camera.world_to_screen(upos)

            for idx, cmd in enumerate(unit._command_queue, start=1):
                tx = cmd.get("target_x", 0)
                ty = cmd.get("target_y", 0)
                target_world = Vec2(tx * 32, ty * 32)
                target_screen = camera.world_to_screen(target_world)

                start_pos = (int(prev_screen[0]), int(prev_screen[1]))
                end_pos = (int(target_screen[0]), int(target_screen[1]))

                cmd_type = cmd.get("type", "move")
                if cmd_type == "attack":
                    self._draw_dashed_line(start_pos, end_pos, (255, 165, 0), dash_len=6)
                    # Attack marker: orange crosshair
                    pygame.draw.circle(offscreen, (255, 165, 0), end_pos, 5, 1)
                    pygame.draw.line(offscreen, (255, 165, 0), (end_pos[0] - 7, end_pos[1]), (end_pos[0] + 7, end_pos[1]), 1)
                    pygame.draw.line(offscreen, (255, 165, 0), (end_pos[0], end_pos[1] - 7), (end_pos[0], end_pos[1] + 7), 1)
                else:
                    self._draw_dashed_line(start_pos, end_pos, (0, 220, 220), dash_len=6)
                    # Move marker: cyan circle
                    pygame.draw.circle(offscreen, (0, 220, 220), end_pos, 4, 1)

                # Waypoint number (CC2-authentic: execution order badge)
                try:
                    font = pygame.font.Font(None, 18)
                    num_text = str(idx)
                    num_surf = font.render(num_text, True, (255, 255, 255))
                    # Black outline for legibility
                    outline_surf = font.render(num_text, True, (0, 0, 0))
                    badge_x = end_pos[0] + 6
                    badge_y = end_pos[1] - 8
                    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                        offscreen.blit(outline_surf, (badge_x + dx, badge_y + dy))
                    offscreen.blit(num_surf, (badge_x, badge_y))
                except (AttributeError, ValueError):
                    pass

                prev_screen = target_screen

    # ------------------------------------------------------------------ #
    #  LOS Overlay
    # ------------------------------------------------------------------ #

    def render_los_overlay(
        self, surface: pygame.Surface, unit, game_map: GameMap, camera: Camera
    ) -> None:
        """Render line-of-sight visualization for the selected unit.

        Called when Ctrl key is held down. Shows visible/hidden areas.
        """
        if unit is None or game_map is None:
            return

        from pycc2.domain.systems.los_system import LOSSystem
        from pycc2.domain.value_objects.tile_coord import TileCoord

        los = LOSSystem(game_map)
        ux = unit.position.tile_coord.x
        uy = unit.position.tile_coord.y
        tile_size = self._ctx.tile_size

        # Lazy-init or resize LOS overlay surface
        overlay_size = (game_map.width * tile_size, game_map.height * tile_size)
        if self._los_overlay is None or self._los_overlay_size != overlay_size:
            self._los_overlay = pygame.Surface(overlay_size, pygame.SRCALPHA)
            self._los_overlay_size = overlay_size
        self._los_overlay.fill((0, 0, 0, 0))

        vision_range = getattr(unit, "vision", None)
        max_range = vision_range.range_tiles if vision_range else 10

        for ty in range(max(0, uy - max_range), min(game_map.height, uy + max_range + 1)):
            for tx in range(max(0, ux - max_range), min(game_map.width, ux + max_range + 1)):
                if tx == ux and ty == uy:
                    continue

                from_coord = TileCoord(ux, uy)
                to_coord = TileCoord(tx, ty)
                can_see, _ = los.check_los(from_coord, to_coord, max_range)
                screen_x = tx * tile_size
                screen_y = ty * tile_size

                if can_see:
                    pygame.draw.rect(
                        self._los_overlay,
                        (0, 255, 0, 25),
                        (screen_x, screen_y, tile_size, tile_size),
                    )
                else:
                    pygame.draw.rect(
                        self._los_overlay,
                        (255, 0, 0, 40),
                        (screen_x, screen_y, tile_size, tile_size),
                    )

        # Blit overlay offset by camera
        cam_x = int(camera.offset_x) if hasattr(camera, "offset_x") else 0
        cam_y = int(camera.offset_y) if hasattr(camera, "offset_y") else 0
        surface.blit(self._los_overlay, (-cam_x, -cam_y))

    # ------------------------------------------------------------------ #
    #  Internal Utilities
    # ------------------------------------------------------------------ #

    def _draw_dashed_line(
        self,
        start: tuple[int, int],
        end: tuple[int, int],
        color: tuple[int, int, int],
        dash_len: int = 8,
    ) -> None:
        """Draw a dashed line on the offscreen buffer."""
        if self._ctx.offscreen is None:
            return
        draw_dashed_line(
            self._ctx.offscreen, color, start, end, dash_length=dash_len, gap_length=dash_len
        )

    # ------------------------------------------------------------------ #
    #  HUD & Debug Grid
    # ------------------------------------------------------------------ #

    def render_hud(self, hud, hud_enabled: bool, dirty_tracker) -> None:
        """Render HUD overlay."""
        if not hud_enabled or hud is None or self._ctx.offscreen is None:
            return
        hud.render(self._ctx.offscreen)
        # PERF: HUD updates every frame (selection, health bars, etc.)
        if dirty_tracker is not None and not dirty_tracker._full_redraw:
            # Mark bottom HUD area as dirty (CC2 three-panel layout at bottom)
            sw, sh = self._ctx.offscreen.get_size()
            dirty_tracker.mark_dirty(pygame.Rect(0, sh - 120, sw, 120))

    def draw_grid(self, game_map: GameMap, camera: Camera) -> None:
        """Draw grid overlay for debugging.

        ⚠️ RELEASE MODE: 此方法仅在 debug_mode=True 时被调用
        在正式发布版本中，此方法不会被调用，不会产生任何性能开销。
        """
        if self._ctx.offscreen is None:
            return

        bounds = camera.view_bounds
        grid_color = (60, 80, 40, 80)  # Dim grey-green
        tile_size = self._ctx.tile_size

        start_x = max(0, int(bounds[0].x // tile_size))
        end_x = min(game_map.width, int((bounds[1].x // tile_size) + 2))
        start_y = max(0, int(bounds[0].y // tile_size))
        end_y = min(game_map.height, int((bounds[1].y // tile_size) + 2))

        for ty in range(start_y, end_y + 1):
            from pycc2.domain.value_objects.vec2 import Vec2

            start_pos = camera.world_to_screen(Vec2(start_x * tile_size, ty * tile_size))
            end_pos = camera.world_to_screen(Vec2(end_x * tile_size, ty * tile_size))
            pygame.draw.line(
                self._ctx.offscreen,
                grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])),
                1,
            )

        for tx in range(start_x, end_x + 1):
            start_pos = camera.world_to_screen(Vec2(tx * tile_size, start_y * tile_size))
            end_pos = camera.world_to_screen(Vec2(tx * tile_size, end_y * tile_size))
            pygame.draw.line(
                self._ctx.offscreen,
                grid_color[:3],
                (int(start_pos[0]), int(start_pos[1])),
                (int(end_pos[0]), int(end_pos[1])),
                1,
            )
