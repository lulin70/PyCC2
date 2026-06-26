"""Soldier monitor and detail popup rendering for the CC2 bottom panel."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pygame import Rect, Surface, draw

if TYPE_CHECKING:
    from pycc2.presentation.rendering.cc2_bottom_panel import CC2BottomPanel


class SoldierMonitorRenderer:
    """Renders the squad-member monitor and right-click soldier detail popup."""

    def __init__(self, panel: CC2BottomPanel) -> None:
        self._panel = panel

    def render(self, surface: Surface, x: int, y: int, w: int, h: int, squad: object) -> None:
        """Render soldier monitor showing individual squad member details.

        Displays:
        - State icon (OK healthy, W wounded, X dead, P pinned, S surrendered)
        - Personal name (e.g., "Pvt. Johnson")
        - Weapon type name (e.g., "M1 Garand", "Thompson")
        - HP bar for each member
        - Ammo bar showing remaining ammo percentage
        - Morale status text (Rallied/Wavering/Pinned/Broken/Routing)
        - Experience level
        """
        # Weapon name mapping by role
        WEAPON_NAMES = {
            "rifleman": "M1 Garand",
            "grenadier": "M1 Carbine",
            "mg_gunner": "MG42",
            "mg_assistant": "MG42",
            "ammo_bearer": "M1 Garand",
            "sniper": "Springfield",
            "spotter": "M1 Garand",
            "at_gunner": "Bazooka",
            "at_assistant": "M1 Garand",
            "mortar_gunner": "60mm Mortar",
            "team_leader": "Thompson",
            "commander": "Colt .45",
            "officer": "Colt .45",
            "gunner": "Thompson",
            "loader": "M1 Garand",
            "driver": "M1 Garand",
            "assistant_driver": "M1 Garand",
            "radioman": "M1 Garand",
            "runner": "M1 Garand",
        }

        # Morale status text mapping
        MORALE_STATUS = {
            "healthy": "Rallied",
            "wounded": "Wavering",
            "pinned": "Pinned",
            "dead": "Dead",
            "surrendered": "Routing",
        }

        # Separator line
        draw.line(surface, (45, 48, 55), (x, y), (x + w, y), 1)
        y += 3

        # Title
        title = self._panel._font_small.render("SQUAD MEMBERS", True, self._panel.HIGHLIGHT_COLOR)
        surface.blit(title, (x + 5, y))
        y += 16

        members = getattr(squad, "members", [])
        member_line_h = 14
        # State icon mapping
        state_icons = {
            "healthy": "OK",
            "wounded": "W",
            "pinned": "P",
            "dead": "X",
            "surrendered": "S",
        }
        state_colors = {
            "healthy": (80, 200, 80),
            "wounded": (255, 200, 50),
            "pinned": (255, 220, 50),
            "dead": (200, 60, 60),
            "surrendered": (150, 150, 150),
        }

        # Experience level labels
        XP_LEVELS = [
            (80, "Vet", (255, 215, 0)),
            (50, "Reg", (100, 200, 255)),
            (25, "Trn", (180, 180, 180)),
            (0, "Rct", (150, 150, 150)),
        ]

        # Track member rects for right-click interaction
        self._panel._soldier_member_rects = []
        start_y = y

        for member in members:
            if y + member_line_h > start_y + h:
                break

            state_name = member.state.value if hasattr(member.state, "value") else str(member.state)
            icon = state_icons.get(state_name, "?")
            icon_color = state_colors.get(state_name, (180, 180, 180))

            # Track clickable rect for this member
            member_rect = Rect(x + 2, y, w - 4, member_line_h)
            self._panel._soldier_member_rects.append((member_rect, member))

            # Highlight if this is the popup member
            if member is self._panel._active_popup_member:
                draw.rect(surface, (50, 55, 70), member_rect)

            # State icon
            icon_surf = self._panel._font_small.render(icon, True, icon_color)
            surface.blit(icon_surf, (x + 5, y))

            # Personal name (e.g., "Pvt. Johnson") — fall back to role if no name
            personal_name = getattr(member, "name", "")
            if not personal_name:
                personal_name = getattr(member, "role", "?")
            display_name = personal_name[:12]
            name_surf = self._panel._font_small.render(display_name, True, self._panel.TEXT_COLOR)
            surface.blit(name_surf, (x + 18, y))

            # Weapon type name
            role = getattr(member, "role", "rifleman")
            weapon_name = WEAPON_NAMES.get(role, "M1 Garand")
            weapon_surf = self._panel._font_small.render(weapon_name[:10], True, (150, 180, 210))
            surface.blit(weapon_surf, (x + 95, y))

            # HP bar
            hp = getattr(member, "hp", 0)
            hp_bar_x = x + 155
            hp_bar_w = 30
            hp_ratio = max(0, min(1, hp / 100))
            draw.rect(surface, (40, 42, 48), Rect(hp_bar_x, y + 2, hp_bar_w, 9))
            hp_color = (
                (80, 200, 80)
                if hp_ratio > 0.5
                else (255, 200, 50)
                if hp_ratio > 0.25
                else (220, 60, 60)
            )
            draw.rect(
                surface,
                hp_color,
                Rect(hp_bar_x, y + 2, int(hp_bar_w * hp_ratio), 9),
            )

            # Ammo bar (small bar showing remaining ammo percentage)
            ammo_bar_x = hp_bar_x + hp_bar_w + 3
            ammo_bar_w = 20
            # Estimate ammo based on role and state
            ammo_ratio = 1.0 if state_name == "healthy" else 0.6 if state_name == "wounded" else 0.0
            draw.rect(surface, (40, 42, 48), Rect(ammo_bar_x, y + 2, ammo_bar_w, 9))
            ammo_color = (
                (100, 150, 255)
                if ammo_ratio > 0.5
                else (200, 150, 50)
                if ammo_ratio > 0.2
                else (200, 60, 60)
            )
            draw.rect(
                surface,
                ammo_color,
                Rect(ammo_bar_x, y + 2, int(ammo_bar_w * ammo_ratio), 9),
            )

            # Morale status text
            morale_text = MORALE_STATUS.get(state_name, "?")
            morale_color = state_colors.get(state_name, (180, 180, 180))
            morale_surf = self._panel._font_small.render(morale_text[:5], True, morale_color)
            surface.blit(morale_surf, (x + w - 38, y))

            # Experience level indicator
            xp = getattr(member, "experience", 0)
            xp_label = "Rct"
            xp_color = (150, 150, 150)
            for threshold, label, color in XP_LEVELS:
                if xp >= threshold:
                    xp_label = label
                    xp_color = color
                    break
            xp_surf = self._panel._font_small.render(xp_label, True, xp_color)
            surface.blit(xp_surf, (x + w - 60, y))

            y += member_line_h

        # Render soldier detail popup if active
        if (
            self._panel._active_popup_member is not None
            and self._panel._active_popup_rect is not None
        ):
            self._render_soldier_detail_popup(
                surface,
                self._panel._active_popup_member,
                self._panel._active_popup_rect,
            )

    def _render_soldier_detail_popup(
        self, surface: Surface, member: object, popup_pos: Rect
    ) -> None:
        """Render a detail popup for a right-clicked soldier.

        Shows:
        - Full name and rank
        - Weapon and ammo count
        - Health and morale status
        - Experience level
        """
        popup_w = 180
        popup_h = 90
        # Position popup near the click, but keep it on screen
        px = min(popup_pos.x, surface.get_width() - popup_w - 5)
        py = min(popup_pos.y, surface.get_height() - popup_h - 5)
        py = max(py, 5)

        # Popup background
        popup_rect = Rect(px, py, popup_w, popup_h)
        draw.rect(surface, (25, 28, 35), popup_rect)
        draw.rect(surface, (120, 130, 150), popup_rect, 1)
        # Inner border
        draw.rect(
            surface,
            (40, 44, 55),
            Rect(px + 1, py + 1, popup_w - 2, popup_h - 2),
            1,
        )

        line_y = py + 5
        line_h = 15

        # Full name and rank
        personal_name = getattr(member, "name", "")
        if not personal_name:
            personal_name = getattr(member, "role", "Unknown")
        name_surf = self._panel._font_normal.render(
            str(personal_name), True, self._panel.HIGHLIGHT_COLOR
        )
        surface.blit(name_surf, (px + 8, line_y))
        line_y += line_h

        # Role
        role = getattr(member, "role", "rifleman")
        role_surf = self._panel._font_small.render(f"Role: {role}", True, (180, 180, 180))
        surface.blit(role_surf, (px + 8, line_y))
        line_y += line_h

        # Weapon
        WEAPON_NAMES = {
            "rifleman": "M1 Garand",
            "grenadier": "M1 Carbine",
            "mg_gunner": "MG42",
            "mg_assistant": "MG42",
            "ammo_bearer": "M1 Garand",
            "sniper": "Springfield",
            "spotter": "M1 Garand",
            "at_gunner": "Bazooka",
            "at_assistant": "M1 Garand",
            "mortar_gunner": "60mm Mortar",
            "team_leader": "Thompson",
            "commander": "Colt .45",
            "officer": "Colt .45",
            "gunner": "Thompson",
            "loader": "M1 Garand",
            "driver": "M1 Garand",
            "assistant_driver": "M1 Garand",
            "radioman": "M1 Garand",
            "runner": "M1 Garand",
        }
        weapon_name = WEAPON_NAMES.get(role, "M1 Garand")
        weapon_surf = self._panel._font_small.render(
            f"Weapon: {weapon_name}", True, (150, 180, 210)
        )
        surface.blit(weapon_surf, (px + 8, line_y))
        line_y += line_h

        # Health
        hp = getattr(member, "hp", 0)
        hp_color = (80, 200, 80) if hp > 50 else (255, 200, 50) if hp > 25 else (220, 60, 60)
        hp_surf = self._panel._font_small.render(f"HP: {hp}/100", True, hp_color)
        surface.blit(hp_surf, (px + 8, line_y))
        line_y += line_h

        # State / Morale
        member_state = getattr(member, "state", None)
        if member_state is None:
            state_name = "unknown"
        elif hasattr(member_state, "value"):
            state_name = member_state.value
        else:
            state_name = str(member_state)
        MORALE_STATUS = {
            "healthy": "Rallied",
            "wounded": "Wavering",
            "pinned": "Pinned",
            "dead": "Dead",
            "surrendered": "Routing",
        }
        morale_text = MORALE_STATUS.get(state_name, "?")
        state_colors = {
            "healthy": (80, 200, 80),
            "wounded": (255, 200, 50),
            "pinned": (255, 220, 50),
            "dead": (200, 60, 60),
            "surrendered": (150, 150, 150),
        }
        morale_color = state_colors.get(state_name, (180, 180, 180))
        morale_surf = self._panel._font_small.render(f"Morale: {morale_text}", True, morale_color)
        surface.blit(morale_surf, (px + 8, line_y))
        line_y += line_h

        # Experience level
        xp = getattr(member, "experience", 0)
        XP_LEVELS = [
            (80, "Veteran"),
            (50, "Regular"),
            (25, "Trained"),
            (0, "Recruit"),
        ]
        xp_label = "Recruit"
        for threshold, label in XP_LEVELS:
            if xp >= threshold:
                xp_label = label
                break
        xp_surf = self._panel._font_small.render(f"XP: {xp} ({xp_label})", True, (200, 200, 200))
        surface.blit(xp_surf, (px + 8, line_y))
