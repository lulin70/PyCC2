"""Report and campaign-end screen rendering mixin — extracted from CampaignUIRenderer.

Extracted during Phase 2 P0-1 (2026-07-04). See ``campaign_ui_rendering.py``
facade for the public API entry point.

Provides:
  - ``_render_report``: post-battle report with narrative elements.
  - ``_generate_narrative_report`` (staticmethod): generate narrative post-battle report text.
  - ``_render_campaign_end``: campaign end screen with historical outcome, casualties, and bridge status.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
from pygame import Rect, Surface, draw

from .campaign_ui_helpers import draw_button, wrap_text

if TYPE_CHECKING:
    from .campaign_ui import CampaignUI


class CampaignUIReportMixin:
    """Mixin: report and campaign-end screens for CampaignUIRenderer.

    Relies on the facade's ``__init__`` to set ``self._ui``.
    """

    # -- Facade attribute set by CampaignUIRenderer.__init__ (typing only) --
    _ui: CampaignUI

    def _render_report(self, surface: Surface) -> None:
        """Render post-battle report with narrative elements."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)

        result = ui._battle_result or {}

        # Victory/Defeat banner
        is_victory = result.get("victory", False)
        victor = result.get("winner", "allies" if is_victory else "axis")
        if is_victory or victor == "allies":
            banner_color = ui.VICTORY_COLOR
            banner_text = "VICTORY"
        elif victor == "axis":
            banner_color = ui.DEFEAT_COLOR
            banner_text = "DEFEAT"
        else:
            banner_color = ui.HIGHLIGHT_COLOR
            banner_text = "DRAW"

        banner_y = ui.MARGIN
        banner_surf = ui._font_title.render(banner_text, True, banner_color)
        surface.blit(banner_surf, (sw // 2 - banner_surf.get_width() // 2, banner_y))

        sep_y = banner_y + banner_surf.get_height() + 8
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # Battle name
        battle_name = result.get("battle_name", "Unknown Battle")
        name_surf = ui._font_normal.render(battle_name, True, ui.HIGHLIGHT_COLOR)
        surface.blit(name_surf, (sw // 2 - name_surf.get_width() // 2, sep_y + 8))

        # Narrative summary section
        narrative_y = sep_y + 36
        narrative_h = sh - narrative_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10

        # Left panel: Narrative battle summary
        left_w = (sw - ui.MARGIN * 3) // 2
        left_x = ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(left_x, narrative_y, left_w, narrative_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(left_x, narrative_y, left_w, narrative_h), 1)

        nar_title = ui._font_normal.render("BATTLE SUMMARY", True, ui.HIGHLIGHT_COLOR)
        surface.blit(nar_title, (left_x + 8, narrative_y + 4))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, narrative_y + 24),
            (left_x + left_w, narrative_y + 24),
            1,
        )

        dy = narrative_y + 30
        narrative_lines = self._generate_narrative_report(result)
        for line in narrative_lines:
            if dy + 16 > narrative_y + narrative_h:
                break
            if line.startswith("---"):
                # Section header
                line_surf = ui._font_normal.render(line, True, ui.HIGHLIGHT_COLOR)
            elif "Killed in Action" in line:
                line_surf = ui._font_small.render(line, True, ui.DEFEAT_COLOR)
            elif any(
                kw in line
                for kw in ["commendation", "heroic", "held the line", "rallied", "distinguished"]
            ):
                line_surf = ui._font_small.render(line, True, ui.COMPLETED_COLOR)
            else:
                line_surf = ui._font_small.render(line, True, (200, 200, 190))
            surface.blit(line_surf, (left_x + 8, dy))
            dy += 16

        # Right panel: Casualties & Experience
        right_x = ui.MARGIN * 2 + left_w
        right_w = sw - right_x - ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, narrative_y, right_w, narrative_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, narrative_y, right_w, narrative_h), 1)

        # Casualties section
        cas_title = ui._font_normal.render("CASUALTIES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(cas_title, (right_x + 8, narrative_y + 4))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, narrative_y + 24),
            (right_x + right_w, narrative_y + 24),
            1,
        )

        dy = narrative_y + 30
        casualties = result.get("casualties", {})
        if casualties:
            for side, data in casualties.items():
                side_label = ui._font_normal.render(f"{side}:", True, ui.TEXT_COLOR)
                surface.blit(side_label, (right_x + 8, dy))
                dy += 20
                if isinstance(data, dict):
                    for key, val in data.items():
                        if dy + 16 > narrative_y + narrative_h:
                            break
                        entry = ui._font_small.render(f"  {key}: {val}", True, (180, 180, 170))
                        surface.blit(entry, (right_x + 8, dy))
                        dy += 16
                else:
                    entry = ui._font_small.render(f"  Total: {data}", True, (180, 180, 170))
                    surface.blit(entry, (right_x + 8, dy))
                    dy += 16
                dy += 6
        else:
            no_data = ui._font_small.render("No casualty data available", True, (128, 128, 128))
            surface.blit(no_data, (right_x + 8, dy))
            dy += 16

        # Experience section
        dy += 10
        exp_title = ui._font_normal.render("EXPERIENCE", True, ui.HIGHLIGHT_COLOR)
        surface.blit(exp_title, (right_x + 8, dy))
        draw.line(surface, ui.BORDER_COLOR, (right_x, dy + 20), (right_x + right_w, dy + 20), 1)
        dy += 26

        experience = result.get("experience", {})
        if experience:
            for key, val in experience.items():
                if dy + 16 > narrative_y + narrative_h:
                    break
                entry = ui._font_small.render(f"  {key}: {val}", True, (180, 180, 170))
                surface.blit(entry, (right_x + 8, dy))
                dy += 16
        else:
            no_data = ui._font_small.render("No experience data available", True, (128, 128, 128))
            surface.blit(no_data, (right_x + 8, dy))

        # Buttons
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._continue_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH * 2 - 10,
            btn_y,
            ui.BUTTON_WIDTH,
            ui.BUTTON_HEIGHT,
        )
        ui._back_button_rect = Rect(
            sw - ui.MARGIN - ui.BUTTON_WIDTH, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )

        draw_button(
            ui, surface, ui._continue_button_rect, "Continue", ui._hovered_button == "continue"
        )
        draw_button(
            ui, surface, ui._back_button_rect, "Back", ui._hovered_button == "back", ui.TEXT_COLOR
        )

    @staticmethod
    def _generate_narrative_report(result: dict) -> list[str]:
        """Generate a narrative post-battle report."""
        lines = []

        # Header
        victor = result.get("winner", "unknown")
        is_victory = result.get("victory", False)
        if is_victory or victor == "allies":
            lines.append("Allied forces have secured the objective!")
        elif victor == "axis":
            lines.append("Axis forces have prevailed.")
        else:
            lines.append("Neither side achieved decisive victory.")

        lines.append("")

        # Key events narrative
        events = result.get("key_events", [])
        if events:
            lines.append("--- Key Events ---")
            for event in events:
                lines.append(f"  {event}")

        # Casualties with names
        allied_kia = result.get("allied_kia", [])
        if allied_kia:
            lines.append("")
            lines.append("--- Fallen ---")
            for name in allied_kia:
                lines.append(f"  {name} - Killed in Action")

        # Heroic actions
        heroic = result.get("heroic_actions", [])
        if heroic:
            lines.append("")
            lines.append("--- Commendations ---")
            for action in heroic:
                lines.append(f"  {action}")

        # If no narrative data, show basic summary
        if not events and not allied_kia and not heroic:
            lines.append("")
            lines.append("--- Summary ---")
            casualties = result.get("casualties", {})
            if casualties:
                for side, data in casualties.items():
                    if isinstance(data, dict):
                        kia = data.get("killed", data.get("KIA", 0))
                        wounded = data.get("wounded", data.get("Wounded", 0))
                        if kia or wounded:
                            lines.append(f"  {side}: {kia} KIA, {wounded} Wounded")
                    else:
                        lines.append(f"  {side}: {data} casualties")
            else:
                lines.append("  No significant casualties reported.")

        return lines

    def _render_campaign_end(self, surface: Surface) -> None:
        """Render the campaign end screen with historical outcome, casualties, and bridge status."""
        ui = self._ui
        assert (
            ui._font_title is not None
            and ui._font_normal is not None
            and ui._font_small is not None
        )
        sw, sh = surface.get_size()
        surface.fill(ui.BG_COLOR)

        summary = ui._campaign_summary or {}
        result = summary.get("result", "DRAW")
        day_ended = summary.get("day_ended", 9)
        allied_cas = summary.get("allied_casualties", {"kia": 0, "wia": 0})
        axis_cas = summary.get("axis_casualties", {"kia": 0, "wia": 0})
        bridge_status = summary.get("bridge_status", {})

        # --- Title banner ---
        if result == "ALLIES_VICTORY":
            banner_color = ui.VICTORY_COLOR
            result_text = "VICTORY"
            subtitle = "XXX Corps reached Arnhem!"
            historical = (
                "The Allied airborne assault succeeded. British 1st Airborne held the "
                "bridge at Arnhem long enough for XXX Corps to relieve them. The road to "
                "the Ruhr lies open."
            )
        elif result == "AXIS_VICTORY":
            banner_color = ui.DEFEAT_COLOR
            result_text = "DEFEAT"
            subtitle = "The Bridge at Arnhem holds"
            historical = (
                "The German defenses proved too strong. The British 1st Airborne was "
                "destroyed at Arnhem, and XXX Corps could not break through in time. "
                "Market Garden has failed."
            )
        else:
            banner_color = ui.HIGHLIGHT_COLOR
            result_text = "DRAW"
            subtitle = "Neither side achieved decisive victory"
            historical = (
                "The operation ended inconclusively. Some objectives were taken, but "
                "the key bridge at Arnhem remains contested. Both sides suffered "
                "heavily."
            )

        # Full-screen overlay with semi-transparent background
        overlay = Surface((sw, sh), pygame.SRCALPHA)
        overlay.fill((20, 24, 30, 230))
        surface.blit(overlay, (0, 0))

        # Title
        header_y = ui.MARGIN + 10
        title_surf = ui._font_title.render("OPERATION MARKET GARDEN", True, ui.HIGHLIGHT_COLOR)
        surface.blit(title_surf, (sw // 2 - title_surf.get_width() // 2, header_y))

        # Result banner
        banner_y = header_y + title_surf.get_height() + 12
        result_surf = ui._font_title.render(result_text, True, banner_color)
        surface.blit(result_surf, (sw // 2 - result_surf.get_width() // 2, banner_y))

        # Subtitle
        sub_y = banner_y + result_surf.get_height() + 8
        sub_surf = ui._font_normal.render(subtitle, True, ui.TEXT_COLOR)
        surface.blit(sub_surf, (sw // 2 - sub_surf.get_width() // 2, sub_y))

        # Separator
        sep_y = sub_y + sub_surf.get_height() + 10
        draw.line(surface, ui.BORDER_COLOR, (ui.MARGIN, sep_y), (sw - ui.MARGIN, sep_y), 1)

        # --- Left panel: Historical text + Bridge status ---
        left_w = (sw - ui.MARGIN * 3) // 2
        left_x = ui.MARGIN
        content_y = sep_y + 10
        content_h = sh - content_y - ui.BUTTON_HEIGHT - ui.MARGIN * 2 - 10

        draw.rect(surface, ui.PANEL_COLOR, Rect(left_x, content_y, left_w, content_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(left_x, content_y, left_w, content_h), 1)

        # Historical text
        hist_title = ui._font_normal.render("HISTORICAL OUTCOME", True, ui.HIGHLIGHT_COLOR)
        surface.blit(hist_title, (left_x + 10, content_y + 8))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, content_y + 28),
            (left_x + left_w, content_y + 28),
            1,
        )

        dy = content_y + 34
        for line in wrap_text(historical, ui._font_normal, left_w - 30):
            if dy + 20 > content_y + content_h // 2:
                break
            ls = ui._font_normal.render(line, True, (200, 200, 190))
            surface.blit(ls, (left_x + 10, dy))
            dy += 22

        # Day ended
        dy += 8
        day_surf = ui._font_normal.render(f"Day {day_ended} of 9", True, ui.HIGHLIGHT_COLOR)
        surface.blit(day_surf, (left_x + 10, dy))

        # Bridge status section
        bridge_section_y = content_y + content_h // 2 + 5
        bridge_title = ui._font_normal.render("BRIDGE STATUS", True, ui.HIGHLIGHT_COLOR)
        surface.blit(bridge_title, (left_x + 10, bridge_section_y))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (left_x, bridge_section_y + 22),
            (left_x + left_w, bridge_section_y + 22),
            1,
        )

        dy = bridge_section_y + 28
        if bridge_status:
            for bridge_name, status in bridge_status.items():
                if dy + 18 > content_y + content_h:
                    break
                if status == "captured_allied":
                    status_color = ui.COMPLETED_COLOR
                    status_label = "Captured (Allied)"
                elif status == "captured_axis":
                    status_color = ui.DEFEAT_COLOR
                    status_label = "Held (Axis)"
                else:
                    status_color = ui.HIGHLIGHT_COLOR
                    status_label = "Contested"
                name_surf = ui._font_small.render(bridge_name, True, ui.TEXT_COLOR)
                surface.blit(name_surf, (left_x + 10, dy))
                status_surf = ui._font_small.render(status_label, True, status_color)
                surface.blit(status_surf, (left_x + left_w - status_surf.get_width() - 10, dy))
                dy += 18
        else:
            no_data = ui._font_small.render("No bridge data available", True, (128, 128, 128))
            surface.blit(no_data, (left_x + 10, dy))

        # --- Right panel: Casualties table ---
        right_x = ui.MARGIN * 2 + left_w
        right_w = sw - right_x - ui.MARGIN
        draw.rect(surface, ui.PANEL_COLOR, Rect(right_x, content_y, right_w, content_h))
        draw.rect(surface, ui.BORDER_COLOR, Rect(right_x, content_y, right_w, content_h), 1)

        cas_title = ui._font_normal.render("TOTAL CASUALTIES", True, ui.HIGHLIGHT_COLOR)
        surface.blit(cas_title, (right_x + 10, content_y + 8))
        draw.line(
            surface,
            ui.BORDER_COLOR,
            (right_x, content_y + 28),
            (right_x + right_w, content_y + 28),
            1,
        )

        # Table header
        dy = content_y + 36
        col_x_side = right_x + 10
        col_x_kia = right_x + right_w // 3
        col_x_wia = right_x + 2 * right_w // 3

        hdr_surf = ui._font_normal.render("Side", True, ui.HIGHLIGHT_COLOR)
        surface.blit(hdr_surf, (col_x_side, dy))
        kia_hdr = ui._font_normal.render("KIA", True, ui.HIGHLIGHT_COLOR)
        surface.blit(kia_hdr, (col_x_kia, dy))
        wia_hdr = ui._font_normal.render("WIA", True, ui.HIGHLIGHT_COLOR)
        surface.blit(wia_hdr, (col_x_wia, dy))

        dy += 26
        draw.line(
            surface, ui.BORDER_COLOR, (right_x + 5, dy - 4), (right_x + right_w - 5, dy - 4), 1
        )

        # Allied row
        allied_label = ui._font_normal.render("Allies", True, ui.COMPLETED_COLOR)
        surface.blit(allied_label, (col_x_side, dy))
        allied_kia = ui._font_normal.render(str(allied_cas.get("kia", 0)), True, ui.DEFEAT_COLOR)
        surface.blit(allied_kia, (col_x_kia, dy))
        allied_wia = ui._font_normal.render(str(allied_cas.get("wia", 0)), True, ui.HIGHLIGHT_COLOR)
        surface.blit(allied_wia, (col_x_wia, dy))

        dy += 28

        # Axis row
        axis_label = ui._font_normal.render("Axis", True, ui.DEFEAT_COLOR)
        surface.blit(axis_label, (col_x_side, dy))
        axis_kia = ui._font_normal.render(str(axis_cas.get("kia", 0)), True, ui.DEFEAT_COLOR)
        surface.blit(axis_kia, (col_x_kia, dy))
        axis_wia = ui._font_normal.render(str(axis_cas.get("wia", 0)), True, ui.HIGHLIGHT_COLOR)
        surface.blit(axis_wia, (col_x_wia, dy))

        # MIA note
        dy += 40
        mia_note = ui._font_small.render(
            "MIA: Included in KIA for campaign accounting", True, (128, 128, 128)
        )
        surface.blit(mia_note, (right_x + 10, dy))

        # --- Buttons ---
        btn_y = sh - ui.BUTTON_HEIGHT - ui.MARGIN
        ui._new_campaign_button_rect = Rect(
            sw // 2 - ui.BUTTON_WIDTH - 10, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT
        )
        ui._main_menu_button_rect = Rect(sw // 2 + 10, btn_y, ui.BUTTON_WIDTH, ui.BUTTON_HEIGHT)

        draw_button(
            ui,
            surface,
            ui._new_campaign_button_rect,
            "New Campaign",
            ui._hovered_button == "new_campaign",
        )
        draw_button(
            ui,
            surface,
            ui._main_menu_button_rect,
            "Main Menu",
            ui._hovered_button == "main_menu",
            ui.TEXT_COLOR,
        )
