"""CC2 HUD rendering logic extracted from CC2HUD.

CC2HUDRenderer handles all drawing operations for the three-panel HUD layout.
It reads state from a CC2HUD instance (passed as ``hud`` parameter).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from pygame import Rect, Surface, draw

from pycc2.domain.entities.unit import Faction
from pycc2.presentation.rendering.pixel_artist_enums import InfantryType

if TYPE_CHECKING:
    from pycc2.domain.entities.unit import Unit


# Unit portrait renderer (Step 1: Integration)
try:
    from pycc2.presentation.ui.unit_portrait_renderer import UnitPortraitRenderer

    _PORTRAIT_RENDERER_AVAILABLE = True
except ImportError:
    _PORTRAIT_RENDERER_AVAILABLE = False
    logger.warning("UnitPortraitRenderer not available - portraits disabled")


class CC2HUDRenderer:
    """Renders all visual elements of the CC2 three-panel HUD."""

    def __init__(self) -> None:
        self._portrait_renderer: UnitPortraitRenderer | None = None
        if _PORTRAIT_RENDERER_AVAILABLE:
            try:
                self._portrait_renderer = UnitPortraitRenderer(max_cache_size=50)
                logger.info("UnitPortraitRenderer initialized successfully")
            except Exception as e:
                logger.warning(f"Failed to initialize UnitPortraitRenderer: {e}")
                self._portrait_renderer = None

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def render(self, hud, surface: Surface) -> None:
        """Render the complete three-panel HUD onto *surface*.

        Args:
            hud: CC2HUD instance providing all state (fonts, units, rects, etc.)
            surface: Target pygame surface (already sized & filled with BG_COLOR)
        """
        # Calculate panel positions
        left_x = 0
        center_x = hud._left_width + hud.PADDING
        right_x = center_x + hud._center_width + hud.PADDING

        content_y = hud.PADDING + 2
        content_h = hud.PANEL_HEIGHT - (hud.PADDING * 2) - 2

        # Render three panels
        self._render_left_panel(hud, surface, left_x + 2, content_y, hud._left_width - 4, content_h)
        self._render_center_panel(hud, surface, center_x, content_y, hud._center_width, content_h)
        self._render_right_panel(hud, surface, right_x, content_y, hud._right_width - 2, content_h)

    # ==================================================================
    # LEFT PANEL – unit roster
    # ==================================================================

    def _render_left_panel(self, hud, surface: Surface, x: int, y: int, w: int, h: int) -> None:
        """Render left panel: unit roster with status indicators."""
        # Panel background
        draw.rect(surface, hud.PANEL_BG_DARK, Rect(x, y, w, h))
        draw.rect(surface, hud.BORDER_COLOR, Rect(x, y, w, h), 1)

        # Title bar with [Hide] button
        title_rect = Rect(x + 4, y + 2, w - 8, 20)
        title_text = "[Hide]"
        title_surf = hud._font_normal.render(title_text, True, hud.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (title_rect.x + 4, title_rect.y + 3))

        # Separator
        sep_y = y + 22
        draw.line(surface, hud.BORDER_COLOR, (x + 4, sep_y), (x + w - 4, sep_y), 1)

        # Unit list
        hud._unit_rects = []
        hud._hide_button_rects = {}
        list_y = sep_y + 4
        list_h = h - 26
        row_h = hud.ROW_HEIGHT

        visible_units = hud._units[hud._scroll_offset : hud._scroll_offset + hud._max_visible_units]

        for i, unit in enumerate(visible_units):
            row_y = list_y + i * row_h
            if row_y + row_h > y + h - 4:
                break

            is_selected = unit.id == hud._selected_unit_id
            row_rect = Rect(x + 4, row_y, w - 8, row_h - 2)

            # Row background (highlighted if selected)
            if is_selected:
                draw.rect(surface, (*hud.HIGHLIGHT_COLOR, 30), row_rect)
                draw.rect(
                    surface, hud.HIGHLIGHT_COLOR, (row_rect.x, row_rect.y, 2, row_rect.height)
                )

            # Status dot (health indicator)
            status_color = self._get_status_color(hud, unit)
            dot_x = x + 8
            dot_y = row_y + row_h // 2
            draw.circle(surface, status_color, (dot_x, dot_y), 4)
            draw.circle(surface, (*status_color, 180), (dot_x, dot_y), 4, 1)

            # Unit type icon (16x16)
            icon_key = self._get_unit_icon_key(unit)
            icon = hud._unit_icons.get(icon_key)
            icon_x = dot_x + 10
            icon_y = row_y + 1
            if icon:
                surface.blit(icon, (icon_x, icon_y))

            # Unit name (truncated to fit)
            name = getattr(unit, "name", "Unknown")[:14]
            name_color = hud.HIGHLIGHT_COLOR if is_selected else hud.TEXT_COLOR
            name_surf = hud._font_normal.render(name, True, name_color)
            surface.blit(name_surf, (icon_x + hud.ICON_SIZE + 4, row_y + 3))

            # Hide button (text button on right)
            hide_text = "Hide"
            hide_surf = hud._font_small.render(hide_text, True, (150, 150, 140))
            hide_w = max(hide_surf.get_width() + 8, hud.BUTTON_MIN_WIDTH // 2)
            hide_rect = Rect(x + w - hide_w - 6, row_y + 2, hide_w, row_h - 4)
            draw.rect(surface, (45, 48, 55), hide_rect)
            draw.rect(surface, (70, 73, 80), hide_rect, 1)
            surface.blit(
                hide_surf,
                (
                    hide_rect.x + (hide_rect.w - hide_surf.get_width()) // 2,
                    hide_rect.y + (hide_rect.h - hide_surf.get_height()) // 2,
                ),
            )

            # Store interaction rects
            hud._unit_rects.append((row_rect, unit.id))
            hud._hide_button_rects[unit.id] = hide_rect

        # Scrollbar indicator
        total = len(hud._units)
        if total > hud._max_visible_units:
            scroll_h = max(20, int(list_h * (hud._max_visible_units / total)))
            scroll_y = list_y + int(
                (list_h - scroll_h) * (hud._scroll_offset / (total - hud._max_visible_units))
            )
            draw.rect(surface, (80, 80, 90), Rect(x + w - 6, scroll_y, 3, scroll_h))

    # ==================================================================
    # CENTER PANEL – selected unit detail
    # ==================================================================

    def _render_center_panel(self, hud, surface: Surface, x: int, y: int, w: int, h: int) -> None:
        """Render center panel: detailed unit status display."""
        # Panel background
        draw.rect(surface, hud.PANEL_BG_MID, Rect(x, y, w, h))
        draw.rect(surface, hud.BORDER_COLOR, Rect(x, y, w, h), 1)

        line_y = y + 4
        line_h = 16

        # === Resource Bar Row ===
        BLOCK = "\u2588"
        ap_text = f"AP:{BLOCK * min(hud._ap_remaining, 10)}"
        at_text = f"AT:{BLOCK * min(hud._at_remaining, 5)}"
        timer_text = f"TIMER {hud._timer}"
        troop_text = "Troop Status"

        resources = f"{ap_text}  {at_text}  {troop_text}  {timer_text}"
        res_surf = hud._font_small.render(resources, True, hud.TEXT_COLOR)
        surface.blit(res_surf, (x + 6, line_y))
        line_y += line_h + 4

        # === Info Mode Toggle ===
        modes = ["ALL", "STYLE", "OFF"]
        mode_spacing = 50
        mode_start_x = x + 6
        hud._info_mode_rects = {}

        for i, mode in enumerate(modes):
            mx = mode_start_x + i * mode_spacing
            mrect = Rect(mx, line_y, 40, 18)
            hud._info_mode_rects[mode] = mrect

            is_active = mode == hud._info_mode.upper()
            bg = (60, 65, 75) if is_active else (40, 43, 50)
            tc = hud.HIGHLIGHT_COLOR if is_active else (140, 140, 135)
            draw.rect(surface, bg, mrect)
            draw.rect(surface, hud.BORDER_COLOR if is_active else (50, 53, 60), mrect, 1)
            msurf = hud._font_small.render(mode, True, tc)
            surface.blit(
                msurf, (mx + (40 - msurf.get_width()) // 2, line_y + (18 - msurf.get_height()) // 2)
            )

        line_y += 22

        # Separator with green tint
        draw.line(surface, (*hud.STATUS_HEALTHY, 150), (x + 4, line_y), (x + w - 4, line_y), 1)
        line_y += 6

        # === Status Bars Section (Morale/AP/AT) ===
        if hud._selected_unit_id:
            unit = next((u for u in hud._units if u.id == hud._selected_unit_id), None)
            if unit:
                # Morale value from unit
                morale_val = getattr(getattr(unit, "morale", None), "value", 75)
                morale_pct = max(0, min(100, morale_val))

                # Morale bar
                self._draw_status_bar(
                    hud,
                    surface,
                    x + 6,
                    line_y,
                    w - 12,
                    14,
                    "Morale",
                    morale_pct,
                    self._get_morale_color(hud, morale_val),
                )
                line_y += 18

                # AP bar
                ap_pct = (hud._ap_remaining / 10) * 100
                self._draw_status_bar(
                    hud, surface, x + 6, line_y, w - 12, 14, "AP", ap_pct, hud.AP_BAR_COLOR
                )
                line_y += 18

                # AT bar
                at_pct = (hud._at_remaining / 5) * 100
                self._draw_status_bar(
                    hud, surface, x + 6, line_y, w - 12, 14, "AT", at_pct, hud.AT_BAR_COLOR
                )
                line_y += 20
            else:
                line_y += 54
        else:
            no_sel = hud._font_normal.render("No unit selected", True, (120, 120, 115))
            surface.blit(no_sel, (x + w // 2 - 50, line_y + 20))
            line_y += 54

        # Separator
        draw.line(surface, (50, 53, 60), (x + 4, line_y), (x + w - 4, line_y), 1)
        line_y += 6

        # === Selected Unit Details ===
        if hud._selected_unit_id:
            unit = next((u for u in hud._units if u.id == hud._selected_unit_id), None)
            if unit:
                self._render_unit_details(hud, surface, x + 6, line_y, w - 12, unit)

    # ==================================================================
    # RIGHT PANEL – commands + minimap
    # ==================================================================

    def _render_right_panel(self, hud, surface: Surface, x: int, y: int, w: int, h: int) -> None:
        """Render right panel: command menu and minimap."""
        # Panel background
        draw.rect(surface, hud.PANEL_BG_LIGHT, Rect(x, y, w, h))
        draw.rect(surface, hud.BORDER_COLOR, Rect(x, y, w, h), 1)

        line_y = y + 4

        # === Command Menu (compact list) ===
        menu_h = len(hud._commands) * 18 + 4
        menu_rect = Rect(x + 4, line_y, w - 8, menu_h)
        draw.rect(surface, (30, 33, 38), menu_rect)
        draw.rect(surface, (50, 53, 60), menu_rect, 1)

        hud._command_button_rects = {}
        for i, cmd in enumerate(hud._commands):
            cmd_y = line_y + 4 + i * 18
            cmd_rect = Rect(x + 6, cmd_y, w - 12, 16)
            hud._command_button_rects[cmd["id"]] = cmd_rect

            is_hovered = cmd["id"] == hud._hovered_command
            bg = (50, 55, 68) if is_hovered else (35, 38, 45)

            draw.rect(surface, bg, cmd_rect)

            # Key marker (● or ○)
            key_color = cmd.get("color", hud.TEXT_COLOR)
            key_surf = hud._font_normal.render(cmd["key"], True, key_color)
            surface.blit(key_surf, (cmd_rect.x + 4, cmd_y + 1))

            # Command label
            label_surf = hud._font_normal.render(cmd["label"], True, hud.TEXT_COLOR)
            surface.blit(label_surf, (cmd_rect.x + 20, cmd_y + 1))

        line_y += menu_h + 8

        # === Current Unit Name (Large) ===
        if hud._selected_unit_id:
            unit = next((u for u in hud._units if u.id == hud._selected_unit_id), None)
            if unit:
                unit_name = getattr(unit, "name", "Unknown")[:16]
                name_surf = hud._font_title.render(unit_name, True, hud.HIGHLIGHT_COLOR)
                # Center the name
                name_x = x + (w - name_surf.get_width()) // 2
                surface.blit(name_surf, (name_x, line_y))
        line_y += 22

        # Separator
        draw.line(surface, (50, 53, 60), (x + 4, line_y), (x + w - 4, line_y), 1)
        line_y += 6

        # === Minimap Preview Area ===
        minimap_size = min(hud.MINIMAP_SIZE, w - 16, h - line_y + y - 80)
        if minimap_size > 40:
            mm_x = x + (w - minimap_size) // 2

            # Sync minimap data before rendering
            hud._minimap.update_units(hud._units)
            hud._minimap.set_selected_unit(hud._selected_unit_id)
            if hud._camera:
                cam = hud._camera
                viewport = (
                    cam.position.x,
                    cam.position.y,
                    cam.viewport_width,
                    cam.viewport_height,
                )
                hud._minimap.set_camera_viewport(viewport)

            # Render the real minimap (terrain + units + viewport)
            hud._minimap.render(surface, mm_x, line_y)

            line_y += minimap_size + 8

        # === Large Command Buttons (bottom section) ===
        if line_y < y + h - 30:
            big_btn_h = 24
            big_cmds = hud._commands[:5]
            btn_w = (w - 12 - (len(big_cmds) - 1) * 4) // len(big_cmds)

            for i, cmd in enumerate(big_cmds):
                btn_x = x + 6 + i * (btn_w + 4)
                btn_y = line_y
                btn_rect = Rect(btn_x, btn_y, btn_w, big_btn_h)

                # Store rect (override compact menu rect)
                hud._command_button_rects[f"{cmd['id']}_large"] = btn_rect

                is_hovered = cmd["id"] == hud._hovered_command
                key_color = cmd.get("color", hud.STATUS_HEALTHY)

                # Button background
                bg_color = (45, 50, 62) if is_hovered else (35, 40, 50)
                draw.rect(surface, bg_color, btn_rect)
                draw.rect(surface, key_color if is_hovered else (60, 65, 75), btn_rect, 1)

                # Status dot
                draw.circle(surface, key_color, (btn_x + 10, btn_y + big_btn_h // 2), 5)

                # Label
                lbl_surf = hud._font_small.render(cmd["label"][:8], True, hud.TEXT_COLOR)
                surface.blit(lbl_surf, (btn_x + 20, btn_y + 6))

                # Mini preview rectangle (right side)
                prev_rect = Rect(btn_x + btn_w - 22, btn_y + 3, 18, 18)
                draw.rect(surface, (30, 33, 38), prev_rect)
                draw.rect(surface, (55, 58, 65), prev_rect, 1)

    # ------------------------------------------------------------------
    # Unit details sub-renderer
    # ------------------------------------------------------------------

    def _render_unit_details(
        self, hud, surface: Surface, x: int, y: int, w: int, unit: Unit
    ) -> None:
        """Render detailed information for selected unit (Step 1: Portrait Integration)."""
        line_y = y
        line_h = 15
        small_line_h = 13

        # === STEP 1: Unit Portrait (96x96) ===
        portrait_rendered = False
        if self._portrait_renderer:
            try:
                # Extract unit attributes for portrait rendering
                infantry_type = getattr(unit, "infantry_type", "RIFLEMAN")
                if hasattr(infantry_type, "name"):
                    infantry_type = infantry_type.name

                faction = getattr(unit, "faction", "ALLY")
                if hasattr(faction, "name"):
                    faction = faction.name

                # Convert to enums expected by portrait renderer
                try:
                    infantry_type_enum = InfantryType[infantry_type]
                except (KeyError, TypeError):
                    infantry_type_enum = InfantryType.RIFLEMAN

                try:
                    faction_enum = Faction[faction]
                except (KeyError, TypeError):
                    faction_enum = Faction.ALLIES

                # Calculate health ratio for damage effects
                hp = getattr(getattr(unit, "health", None), "hp", 100)
                hp_max = getattr(getattr(unit, "health", None), "max_hp", 100)
                health_ratio = hp / max(hp_max, 1)

                # Render 96x96 portrait
                portrait = self._portrait_renderer.render_portrait(
                    infantry_type_enum, faction_enum, health_ratio
                )

                # Display portrait at left side of panel
                if portrait:
                    surface.blit(portrait, (x, line_y))
                    portrait_rendered = True
                    logger.debug(f"Portrait rendered for {infantry_type} ({faction})")

            except Exception as e:
                logger.warning(f"Failed to render portrait: {e}")
                # Fallback to icon rendering below

        # Adjust layout if portrait was rendered
        if portrait_rendered:
            # Portrait takes 96x96, text starts to the right
            name_x = x + 96 + 8
            icon_x = x + 96 + 8
        else:
            # No portrait: use original layout with small icon
            name_x = x + hud.ICON_SIZE + 4
            icon_x = x

            # Fallback: render small 16x16 icon
            icon_key = self._get_unit_icon_key(unit)
            icon = hud._unit_icons.get(icon_key)
            if icon:
                surface.blit(icon, (icon_x, line_y))

        # Unit name
        name = getattr(unit, "name", "Unknown")[:18]
        name_surf = hud._font_normal.render(name, True, hud.HIGHLIGHT_COLOR)
        surface.blit(name_surf, (name_x, line_y + 2))

        # AP dots indicator
        ap_dots = "\u25cf" * min(hud._ap_remaining, 5) + "\u25cb" * max(0, 5 - hud._ap_remaining)
        ap_dot_surf = hud._font_small.render(ap_dots, True, hud.AP_BAR_COLOR)
        surface.blit(ap_dot_surf, (x + w - 50, line_y + 3))
        line_y += line_h + 4

        # Separator
        draw.line(surface, (50, 53, 60), (x, line_y), (x + w, line_y), 1)
        line_y += 4

        # Operational status
        state_machine = getattr(unit, "state_machine", None)
        state_name = getattr(getattr(state_machine, "current", None), "name", "IDLE")
        op_text = f"Operational: {state_name}"
        op_surf = hud._font_small.render(op_text, True, (180, 180, 175))
        surface.blit(op_surf, (x, line_y))
        line_y += small_line_h + 2

        # Attribute bars (Morale, AMMO, AT)
        morale_val = getattr(getattr(unit, "morale", None), "value", 75)
        ammo_val = getattr(getattr(unit, "weapon", None), "ammo_remaining", 30)
        ammo_max = getattr(getattr(unit, "weapon", None), "max_ammo", 30)
        ammo_pct = (ammo_val / max(ammo_max, 1)) * 100

        # Compact inline bars
        bar_w = (w - 100) // 3

        # Morale
        m_text = "Morale:"
        m_surf = hud._font_small.render(m_text, True, hud.TEXT_COLOR)
        surface.blit(m_surf, (x, line_y))
        self._draw_mini_bar(
            surface,
            x + 48,
            line_y,
            bar_w,
            10,
            int(morale_val),
            self._get_morale_color(hud, morale_val),
        )

        # AMMO
        a_text = "AMMO:"
        a_surf = hud._font_small.render(a_text, True, hud.TEXT_COLOR)
        surface.blit(a_surf, (x + bar_w + 52, line_y))
        self._draw_mini_bar(
            surface, x + bar_w + 90, line_y, bar_w, 10, int(ammo_pct), (100, 150, 255)
        )

        # AT
        at_text = "AT:"
        at_surf = hud._font_small.render(at_text, True, hud.TEXT_COLOR)
        surface.blit(at_surf, (x + (bar_w + 38) * 2, line_y))
        self._draw_mini_bar(
            surface,
            x + (bar_w + 38) * 2 + 18,
            line_y,
            bar_w - 10,
            10,
            int((hud._at_remaining / 5) * 100),
            hud.AT_BAR_COLOR,
        )
        line_y += 14

        # Weapon info
        weapon_name = getattr(getattr(unit, "weapon", None), "name", "M1 Garand")
        wpn_text = f"Weapon: {weapon_name[:20]}"
        wpn_surf = hud._font_small.render(wpn_text, True, (170, 175, 170))
        surface.blit(wpn_surf, (x, line_y))
        line_y += small_line_h

        # Crew composition (if squad)
        crew = self._get_crew_string(unit)
        crew_surf = hud._font_small.render(crew, True, (155, 160, 155))
        surface.blit(crew_surf, (x + 8, line_y))
        line_y += small_line_h

        # Additional info lines (if space permits)
        max_y = y + 85
        if line_y < max_y:
            # Target
            target = getattr(unit, "target_name", None)
            if target:
                tgt_text = f"Target: {target[:15]}"
                tgt_surf = hud._font_small.render(tgt_text, True, (160, 165, 160))
                surface.blit(tgt_surf, (x, line_y))
                line_y += small_line_h

        if line_y < max_y:
            # Commander status
            cmdr_health = "Healthy"
            hp_ratio = getattr(getattr(unit, "health", None), "hp", 100) / max(
                getattr(getattr(unit, "health", None), "max_hp", 100), 1
            )
            if hp_ratio < 0.3:
                cmdr_health = "Wounded"
            elif hp_ratio < 0.6:
                cmdr_health = "Injured"

            cmdr_text = f"Commander: {cmdr_health}  Status: Ready"
            cmdr_surf = hud._font_small.render(cmdr_text, True, (155, 160, 155))
            surface.blit(cmdr_surf, (x, line_y))
            line_y += small_line_h

        if line_y < max_y:
            # Vehicle (if applicable)
            vehicle = getattr(unit, "vehicle_name", None)
            if vehicle:
                veh_text = f"Vehicle: {vehicle[:18]}"
                veh_surf = hud._font_small.render(veh_text, True, (155, 160, 155))
                surface.blit(veh_surf, (x, line_y))
                line_y += small_line_h

        if line_y < max_y:
            # Position
            pos = getattr(unit, "location_name", "Unknown")
            pos_text = f"Position: {pos[:18]}"
            pos_surf = hud._font_small.render(pos_text, True, (155, 160, 155))
            surface.blit(pos_surf, (x, line_y))

    # ==================================================================
    # HELPER METHODS
    # ==================================================================

    @staticmethod
    def _get_status_color(hud, unit: Unit) -> tuple[int, int, int]:
        """Get status dot color based on unit health."""
        try:
            hp = getattr(getattr(unit, "health", None), "hp", 100)
            hp_max = getattr(getattr(unit, "health", None), "max_hp", 100)
            ratio = hp / max(hp_max, 1)

            if ratio >= 0.8:
                return hud.STATUS_HEALTHY
            elif ratio >= 0.5:
                return hud.STATUS_WOUNDED
            elif ratio > 0:
                return hud.STATUS_CRITICAL
            else:
                return hud.STATUS_DEAD
        except (TypeError, AttributeError, ZeroDivisionError):
            return hud.STATUS_HEALTHY

    @staticmethod
    def _get_morale_color(hud, value: int) -> tuple[int, int, int]:
        """Get morale bar color based on value."""
        if value >= 70:
            return hud.STATUS_HEALTHY
        elif value >= 45:
            return hud.STATUS_WOUNDED
        elif value >= 20:
            return (255, 140, 50)  # Orange
        else:
            return hud.STATUS_CRITICAL

    @staticmethod
    def _get_unit_icon_key(unit: Unit) -> str:
        """Map unit type to icon cache key."""
        type_name = unit.unit_type.name.lower() if hasattr(unit.unit_type, "name") else ""
        if "tank" in type_name or "armor" in type_name or "vehicle" in type_name:
            return "tank"
        elif "mg" in type_name or "machine" in type_name:
            return "mg"
        elif "sniper" in type_name or "scout" in type_name:
            return "sniper"
        elif "officer" in type_name or "commander" in type_name:
            return "commander"
        elif "at" in type_name or "anti" in type_name:
            return "at"
        elif "mortar" in type_name:
            return "mortar"
        elif "medic" in type_name or "aid" in type_name:
            return "medic"
        elif "engineer" in type_name:
            return "engineer"
        else:
            return "infantry"

    @staticmethod
    def _get_crew_string(unit: Unit) -> str:
        """Generate crew composition string."""
        squad = getattr(unit, "squad_ref", None)
        if squad:
            members = getattr(squad, "members", [])
            if members:
                roles = []
                for m in members[:4]:
                    role = getattr(m, "role", "?")
                    roles.append(role.replace("_", " ").title())
                return f"Crew: {', '.join(roles)}"

        return "Crew: Single operator"

    @staticmethod
    def _draw_status_bar(
        hud,
        surface: Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        label: str,
        pct: int,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a labeled status bar with border."""
        # Label
        label_surf = hud._font_small.render(f"{label}:", True, hud.TEXT_COLOR)
        surface.blit(label_surf, (x, y + (h - label_surf.get_height()) // 2))

        # Bar background with border
        bar_x = x + label_surf.get_width() + 6
        bar_w = w - label_surf.get_width() - 10
        draw.rect(surface, (35, 38, 43), Rect(bar_x - 1, y - 1, bar_w + 2, h + 2))
        draw.rect(surface, (50, 53, 60), Rect(bar_x, y, bar_w, h))

        # Fill
        fill_w = int(bar_w * pct / 100)
        if fill_w > 0:
            draw.rect(surface, color, Rect(bar_x, y, fill_w, h))

    @staticmethod
    def _draw_mini_bar(
        surface: Surface,
        x: int,
        y: int,
        w: int,
        h: int,
        pct: int,
        color: tuple[int, int, int],
    ) -> None:
        """Draw a compact mini bar without label."""
        draw.rect(surface, (35, 38, 43), Rect(x, y, w, h))
        fill_w = int(w * pct / 100)
        if fill_w > 0:
            draw.rect(surface, color, Rect(x, y, fill_w, h))

    # ------------------------------------------------------------------
    # Icon factories (called during HUD initialization)
    # ------------------------------------------------------------------

    @staticmethod
    def create_unit_icons(hud) -> dict[str, Surface]:
        """Generate 16x16 procedural unit type icons."""
        from pycc2.presentation.ui.hud_constants import BG_COLOR as _BG

        icons: dict[str, Surface] = {}
        bg = _BG

        # Infantry
        s = Surface((16, 16))
        s.fill(bg)
        green = (80, 200, 80)
        dark_green = (50, 150, 50)
        draw.ellipse(s, dark_green, (5, 1, 6, 4))
        draw.line(s, dark_green, (4, 4), (12, 4), 1)
        draw.rect(s, green, (5, 6, 6, 5))
        draw.line(s, green, (5, 7), (3, 9), 1)
        draw.line(s, green, (10, 7), (12, 9), 1)
        draw.line(s, dark_green, (6, 11), (5, 14), 2)
        draw.line(s, dark_green, (9, 11), (10, 14), 2)
        icons["infantry"] = s

        # Tank
        s = Surface((16, 16))
        s.fill(bg)
        tank_gray = (160, 160, 170)
        tank_dark = (120, 120, 130)
        draw.rect(s, tank_gray, (2, 8, 12, 5))
        draw.rect(s, tank_dark, (4, 5, 6, 4))
        draw.line(s, (100, 100, 110), (10, 7), (15, 5), 2)
        draw.rect(s, (80, 80, 90), (1, 12, 14, 2))
        icons["tank"] = s

        # MG
        s = Surface((16, 16))
        s.fill(bg)
        draw.circle(s, (80, 200, 80), (5, 4), 2)
        draw.rect(s, (80, 200, 80), (4, 6, 3, 4))
        draw.line(s, (200, 200, 80), (7, 7), (15, 5), 2)
        draw.rect(s, (100, 100, 60), (7, 6, 4, 3))
        icons["mg"] = s

        # Sniper
        s = Surface((16, 16))
        s.fill(bg)
        draw.ellipse(s, (50, 150, 50), (4, 0, 6, 4))
        draw.line(s, (50, 150, 50), (3, 3), (11, 3), 1)
        draw.rect(s, (80, 200, 80), (4, 5, 6, 4))
        draw.line(s, (60, 60, 60), (11, 5), (15, 1), 1)
        draw.rect(s, (100, 180, 255), (12, 3, 3, 2))
        icons["sniper"] = s

        # Commander
        s = Surface((16, 16))
        s.fill(bg)
        draw.rect(s, (50, 80, 50), (4, 0, 7, 3))
        draw.line(s, (50, 80, 50), (3, 3), (12, 3), 1)
        draw.rect(s, (255, 230, 80), (7, 1, 2, 1))
        draw.rect(s, (80, 200, 80), (4, 5, 6, 5))
        draw.rect(s, (70, 70, 80), (10, 4, 4, 5))
        draw.line(s, (180, 180, 190), (12, 4), (12, 0), 1)
        icons["commander"] = s

        # AT
        s = Surface((16, 16))
        s.fill(bg)
        draw.rect(s, (200, 80, 60), (2, 6, 10, 4))
        draw.polygon(s, (150, 50, 40), [(12, 6), (15, 8), (12, 10)])
        draw.polygon(s, (150, 50, 40), [(2, 6), (4, 3), (5, 6)])
        draw.polygon(s, (150, 50, 40), [(2, 10), (4, 13), (5, 10)])
        icons["at"] = s

        # Mortar
        s = Surface((16, 16))
        s.fill(bg)
        draw.line(s, (140, 140, 150), (4, 14), (10, 4), 3)
        draw.circle(s, (100, 100, 110), (10, 4), 2)
        draw.rect(s, (100, 100, 110), (2, 13, 4, 2))
        icons["mortar"] = s

        # Medic
        s = Surface((16, 16))
        s.fill(bg)
        draw.circle(s, (60, 120, 60), (8, 8), 6)
        draw.rect(s, (240, 240, 240), (6, 3, 4, 10))
        draw.rect(s, (240, 240, 240), (3, 6, 10, 4))
        icons["medic"] = s

        # Engineer
        s = Surface((16, 16))
        s.fill(bg)
        draw.line(s, (120, 120, 130), (3, 13), (10, 6), 2)
        draw.line(s, (180, 180, 190), (8, 4), (10, 6), 2)
        draw.line(s, (180, 180, 190), (10, 6), (12, 4), 2)
        draw.circle(s, (80, 200, 80), (4, 3), 2)
        draw.line(s, (80, 200, 80), (4, 5), (4, 8), 1)
        icons["engineer"] = s

        return icons

    @staticmethod
    def create_command_icons(hud) -> dict[str, Surface]:
        """Generate 24x24 procedural command icons."""
        from pycc2.presentation.ui.hud_constants import BG_COLOR as _BG

        icons: dict[str, Surface] = {}
        bg = _BG

        # Move
        s = Surface((24, 24))
        s.fill(bg)
        green = (80, 220, 80)
        draw.rect(s, green, (6, 14, 12, 5))
        draw.polygon(s, green, [(8, 14), (14, 14), (12, 6), (10, 6)])
        draw.rect(s, green, (6, 10, 4, 4))
        icons["move"] = s

        # Move Fast
        s = Surface((24, 24))
        s.fill(bg)
        bright = (100, 255, 100)
        draw.circle(s, bright, (10, 4), 3)
        draw.line(s, bright, (10, 7), (12, 14), 2)
        draw.line(s, bright, (10, 9), (6, 11), 2)
        draw.line(s, bright, (10, 9), (15, 8), 2)
        draw.line(s, bright, (12, 14), (7, 19), 2)
        draw.line(s, bright, (12, 14), (17, 19), 2)
        draw.polygon(s, bright, [(18, 10), (22, 13), (18, 16)])
        icons["move_fast"] = s

        # Crawl
        s = Surface((24, 24))
        s.fill(bg)
        olive = (140, 180, 80)
        draw.circle(s, olive, (8, 10), 3)
        draw.line(s, olive, (8, 12), (16, 12), 2)
        draw.line(s, olive, (8, 12), (6, 16), 2)
        draw.line(s, olive, (6, 16), (8, 19), 2)
        draw.line(s, olive, (14, 12), (19, 10), 2)
        icons["crawl"] = s

        # Fire
        s = Surface((24, 24))
        s.fill(bg)
        red = (255, 60, 60)
        cx, cy = 12, 12
        draw.circle(s, red, (cx, cy), 9, 1)
        draw.circle(s, red, (cx, cy), 4, 1)
        draw.circle(s, red, (cx, cy), 1)
        draw.line(s, red, (cx, cy - 11), (cx, cy - 5), 1)
        draw.line(s, red, (cx, cy + 5), (cx, cy + 11), 1)
        draw.line(s, red, (cx - 11, cy), (cx - 5, cy), 1)
        draw.line(s, red, (cx + 5, cy), (cx + 11, cy), 1)
        icons["fire"] = s

        # Smoke
        s = Surface((24, 24))
        s.fill(bg)
        gray = (180, 180, 180)
        draw.circle(s, gray, (8, 15), 5)
        draw.circle(s, (210, 210, 210), (14, 13), 6)
        draw.circle(s, (140, 140, 140), (11, 9), 5)
        draw.circle(s, gray, (6, 11), 4)
        icons["smoke"] = s

        # Defend
        s = Surface((24, 24))
        s.fill(bg)
        shield = (100, 160, 255)
        pts = [(12, 1), (22, 6), (22, 14), (12, 22), (2, 14), (2, 6)]
        draw.polygon(s, shield, pts)
        inner = [(12, 4), (19, 8), (19, 13), (12, 19), (5, 13), (5, 8)]
        draw.polygon(s, (50, 80, 140), inner)
        draw.polygon(s, (200, 220, 255), [(7, 7), (12, 13), (17, 7)])
        icons["defend"] = s

        # Hide
        s = Surface((24, 24))
        s.fill(bg)
        eye = (180, 200, 220)
        epts = [(2, 12), (6, 7), (12, 6), (18, 7), (22, 12), (18, 17), (12, 18), (6, 17)]
        draw.polygon(s, eye, epts, 2)
        draw.circle(s, (100, 150, 200), (12, 12), 3)
        draw.circle(s, (40, 40, 40), (12, 12), 1)
        draw.line(s, (255, 60, 60), (4, 4), (20, 20), 2)
        icons["hide"] = s

        return icons
