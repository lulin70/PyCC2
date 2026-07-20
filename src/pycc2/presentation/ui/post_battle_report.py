"""V-03 (Wave C5): Enhanced post-battle report with charts and statistics.

Replaces the basic ``_render_report`` (in campaign_ui_report_mixin.py) when
new ``BattleResult`` schema fields (events / mvp_unit_id) are present.
Falls back to ``_render_report`` when fields are missing (backward compat).

Layout (1280×720)::
    ┌─────────────────────────────────────────┐
    │ TOP: Victory/Defeat banner (height=80)  │
    ├──────────────┬──────────────────────────┤
    │ LEFT:        │ RIGHT:                   │
    │ Casualty     │ Key events timeline      │
    │ statistics   │ (5-10 critical events)   │
    │ (bar chart)  │ tab 切换 (Wave B-rev)    │
    │ (height=300) │ (height=300)             │
    ├──────────────┴──────────────────────────┤
    │ BOTTOM: MVP unit showcase (height=200)  │
    └─────────────────────────────────────────┘

Reference: docs/VISUAL_POLISH_PLAN.md V-03 章节 (v2.1, Wave B-rev)
"""

from __future__ import annotations

from pygame import Rect, Surface, draw
from pygame.font import Font

from pycc2.domain.systems.battle_result import (
    BattleEvent,
    BattleOutcome,
    BattleResult,
    UnitBattleRecord,
)
from pycc2.presentation.ui.campaign_ui_types import (
    BG_COLOR,
    BORDER_COLOR,
    COMPLETED_COLOR,
    DEFEAT_COLOR,
    HIGHLIGHT_COLOR,
    MARGIN,
    PANEL_COLOR,
    TEXT_COLOR,
    VICTORY_COLOR,
)

# Layout constants (1280×720 reference resolution)
BANNER_HEIGHT = 80
MIDDLE_HEIGHT = 300
MVP_HEIGHT = 200
TAB_HEIGHT = 30


# ============================================================================
# MVP Algorithm
# ============================================================================


# Default battle duration for survival normalization (10 minutes in seconds)
DEFAULT_BATTLE_DURATION_SECONDS = 600.0

# MVP score weights (Wave B-rev PM: explicit weights)
MVP_WEIGHT_HIT_RATE = 0.4
MVP_WEIGHT_KILLS = 0.3
MVP_WEIGHT_SURVIVAL = 0.3

# Kill score normalization: 1 kill = 0.1 score (so 10 kills = 1.0 normalized)
MVP_KILL_NORMALIZATION = 0.1


def calculate_mvp(
    unit_records: list[UnitBattleRecord],
    battle_duration_seconds: float = DEFAULT_BATTLE_DURATION_SECONDS,
) -> str | None:
    """V-03 (Wave C5): Calculate MVP unit based on weighted score.

    MVP score formula (Wave B-rev PM: weights explicit)::
        score = hit_rate * 0.4 + kills_normalized * 0.3 + survival_normalized * 0.3

    Where:
        hit_rate = shots_hit / max(shots_fired, 1)
        kills_normalized = min(kills * 0.1, 1.0)  # 10 kills = 1.0
        survival_normalized = min(survival_time / battle_duration, 1.0)

    Args:
        unit_records: List of per-unit battle records.
        battle_duration_seconds: Total battle duration for survival normalization.
            Defaults to 600 seconds (10 minutes).

    Returns:
        unit_id of the highest-scoring unit, or None if no records exist.
    """
    if not unit_records:
        return None

    best_unit: str | None = None
    best_score = -1.0

    for record in unit_records:
        hit_rate = record.shots_hit / max(record.shots_fired, 1)
        kills_normalized = min(record.kills * MVP_KILL_NORMALIZATION, 1.0)
        # Survival time approximation: if survived, full duration; else, half
        # (UnitBattleRecord doesn't track exact death time, so we approximate)
        survival_time = battle_duration_seconds if record.survived else battle_duration_seconds * 0.5
        survival_normalized = min(survival_time / battle_duration_seconds, 1.0)

        score = (
            hit_rate * MVP_WEIGHT_HIT_RATE
            + kills_normalized * MVP_WEIGHT_KILLS
            + survival_normalized * MVP_WEIGHT_SURVIVAL
        )

        if score > best_score:
            best_score = score
            best_unit = record.unit_id

    return best_unit


# ============================================================================
# PostBattleReportRenderer
# ============================================================================


class PostBattleReportRenderer:
    """Enhanced post-battle report with charts and statistics.

    Integrates with existing CampaignUIReportMixin via facade extension.
    Replaces ``_render_report`` when new schema fields are present;
    falls back to ``_render_report`` when fields are missing (backward compat).

    Usage::
        renderer = PostBattleReportRenderer(font_title, font_normal, font_small)
        renderer.render_enhanced_report(surface, battle_result)
    """

    def __init__(
        self,
        font_title: Font,
        font_normal: Font,
        font_small: Font,
        current_tab: str = "casualty",
    ) -> None:
        """Initialize the renderer with fonts and default tab.

        Args:
            font_title: Large font for banner (32pt).
            font_normal: Medium font for section titles (18pt).
            font_small: Small font for body text (14pt).
            current_tab: Initial tab — "casualty" or "events".
                Tab switching is handled externally via ``set_tab()``.
        """
        self._font_title = font_title
        self._font_normal = font_normal
        self._font_small = font_small
        self._current_tab = current_tab if current_tab in ("casualty", "events") else "casualty"

    def set_tab(self, tab: str) -> None:
        """Switch between casualty chart and event timeline tabs.

        Args:
            tab: "casualty" or "events". Invalid values are ignored.
        """
        if tab in ("casualty", "events"):
            self._current_tab = tab

    @property
    def current_tab(self) -> str:
        """Return the current active tab."""
        return self._current_tab

    def render_enhanced_report(self, surface: Surface, battle_result: BattleResult) -> None:
        """Render enhanced post-battle report.

        Args:
            surface: Target surface (1280×720 reference resolution).
            battle_result: BattleResult @dataclass with events/mvp_unit_id fields.
        """
        surface.fill(BG_COLOR)

        self._render_banner(surface, battle_result)

        # Wave B-rev: tab switching to reduce single-screen info density
        if self._current_tab == "casualty":
            self._render_casualty_chart(surface, battle_result)
        else:
            self._render_event_timeline(surface, battle_result)

        self._render_mvp_unit(surface, battle_result)

    # ========================================================================
    # Banner rendering
    # ========================================================================

    def _render_banner(self, surface: Surface, battle_result: BattleResult) -> None:
        """Render victory/defeat banner at the top (height=80).

        Layout:
            - Banner text (VICTORY/DEFEAT/DRAW) centered, 32pt
            - Battle name below banner text
        """
        sw, _ = surface.get_size()

        # Determine banner color and text
        if battle_result.is_victory:
            banner_color = VICTORY_COLOR
            banner_text = "VICTORY"
        elif battle_result.outcome == BattleOutcome.DEFEAT:
            banner_color = DEFEAT_COLOR
            banner_text = "DEFEAT"
        elif battle_result.outcome == BattleOutcome.TIME_OUT_DEFEAT:
            banner_color = DEFEAT_COLOR
            banner_text = "DEFEAT (TIME OUT)"
        else:
            banner_color = HIGHLIGHT_COLOR
            banner_text = "DRAW"

        # Render banner text
        banner_surf = self._font_title.render(banner_text, True, banner_color)
        banner_x = sw // 2 - banner_surf.get_width() // 2
        banner_y = MARGIN
        surface.blit(banner_surf, (banner_x, banner_y))

        # Render battle name
        name_surf = self._font_normal.render(
            battle_result.mission_name or battle_result.mission_id,
            True,
            HIGHLIGHT_COLOR,
        )
        name_x = sw // 2 - name_surf.get_width() // 2
        name_y = banner_y + banner_surf.get_height() + 4
        surface.blit(name_surf, (name_x, name_y))

        # Separator line
        sep_y = MARGIN + BANNER_HEIGHT
        draw.line(surface, BORDER_COLOR, (MARGIN, sep_y), (sw - MARGIN, sep_y), 1)

    # ========================================================================
    # Casualty chart rendering
    # ========================================================================

    def _render_casualty_chart(self, surface: Surface, battle_result: BattleResult) -> None:
        """Render casualty statistics as bar chart (height=300).

        Chart shows two factions (Allies / Axis) with three bars each:
            - Killed (red)
            - Routed (yellow)
            - Survived (green)

        Bar heights are proportional to unit counts.
        """
        sw, _ = surface.get_size()
        chart_y = MARGIN + BANNER_HEIGHT + MARGIN
        chart_h = MIDDLE_HEIGHT

        # Calculate survived counts from unit_records
        allies_total = sum(1 for r in battle_result.unit_records if r.faction == "allies")
        axis_total = sum(1 for r in battle_result.unit_records if r.faction == "axis")
        allies_survived = sum(
            1 for r in battle_result.unit_records
            if r.faction == "allies" and r.survived
        )
        axis_survived = sum(
            1 for r in battle_result.unit_records
            if r.faction == "axis" and r.survived
        )

        # Fallback to aggregated counts if unit_records is empty
        if allies_total == 0:
            allies_total = battle_result.allies_killed + battle_result.allies_routed + 1
            allies_survived = max(0, allies_total - battle_result.allies_killed - battle_result.allies_routed)
        if axis_total == 0:
            axis_total = battle_result.axis_killed + battle_result.axis_routed + 1
            axis_survived = max(0, axis_total - battle_result.axis_killed - battle_result.axis_routed)

        # Section title
        title_surf = self._font_normal.render("CASUALTIES", True, HIGHLIGHT_COLOR)
        surface.blit(title_surf, (MARGIN, chart_y))
        draw.line(
            surface,
            BORDER_COLOR,
            (MARGIN, chart_y + 24),
            (sw - MARGIN, chart_y + 24),
            1,
        )

        # Chart area
        chart_area_y = chart_y + 30
        chart_area_h = chart_h - 60

        # Find max value for scaling
        max_value = max(
            battle_result.allies_killed,
            battle_result.allies_routed,
            allies_survived,
            battle_result.axis_killed,
            battle_result.axis_routed,
            axis_survived,
            1,  # minimum scale
        )

        # Bar layout: 2 groups (Allies, Axis), 3 bars per group
        bar_width = 40
        bar_gap = 8
        group_gap = 60
        group_width = bar_width * 3 + bar_gap * 2

        # Center the chart
        total_chart_width = group_width * 2 + group_gap
        chart_start_x = (sw - total_chart_width) // 2

        # Draw Allies group
        allies_group_x = chart_start_x
        self._draw_casualty_bars(
            surface,
            allies_group_x,
            chart_area_y,
            chart_area_h,
            bar_width,
            bar_gap,
            "ALLIES",
            battle_result.allies_killed,
            battle_result.allies_routed,
            allies_survived,
            max_value,
        )

        # Draw Axis group
        axis_group_x = allies_group_x + group_width + group_gap
        self._draw_casualty_bars(
            surface,
            axis_group_x,
            chart_area_y,
            chart_area_h,
            bar_width,
            bar_gap,
            "AXIS",
            battle_result.axis_killed,
            battle_result.axis_routed,
            axis_survived,
            max_value,
        )

    def _draw_casualty_bars(
        self,
        surface: Surface,
        x: int,
        y: int,
        h: int,
        bar_width: int,
        bar_gap: int,
        label: str,
        killed: int,
        routed: int,
        survived: int,
        max_value: int,
    ) -> None:
        """Draw a group of 3 casualty bars (killed/routed/survived)."""
        # Group label
        label_surf = self._font_normal.render(label, True, HIGHLIGHT_COLOR)
        surface.blit(label_surf, (x, y))

        bar_y_start = y + 24
        bar_h_max = h - 50

        # Killed (red)
        killed_h = int(bar_h_max * killed / max_value) if max_value > 0 else 0
        killed_rect = Rect(x, bar_y_start + bar_h_max - killed_h, bar_width, killed_h)
        draw.rect(surface, DEFEAT_COLOR, killed_rect)
        killed_label = self._font_small.render(str(killed), True, TEXT_COLOR)
        surface.blit(killed_label, (x, bar_y_start + bar_h_max + 4))

        # Routed (yellow)
        routed_x = x + bar_width + bar_gap
        routed_h = int(bar_h_max * routed / max_value) if max_value > 0 else 0
        routed_rect = Rect(routed_x, bar_y_start + bar_h_max - routed_h, bar_width, routed_h)
        draw.rect(surface, HIGHLIGHT_COLOR, routed_rect)
        routed_label = self._font_small.render(str(routed), True, TEXT_COLOR)
        surface.blit(routed_label, (routed_x, bar_y_start + bar_h_max + 4))

        # Survived (green)
        survived_x = routed_x + bar_width + bar_gap
        survived_h = int(bar_h_max * survived / max_value) if max_value > 0 else 0
        survived_rect = Rect(survived_x, bar_y_start + bar_h_max - survived_h, bar_width, survived_h)
        draw.rect(surface, COMPLETED_COLOR, survived_rect)
        survived_label = self._font_small.render(str(survived), True, TEXT_COLOR)
        surface.blit(survived_label, (survived_x, bar_y_start + bar_h_max + 4))

    # ========================================================================
    # Event timeline rendering
    # ========================================================================

    def _render_event_timeline(self, surface: Surface, battle_result: BattleResult) -> None:
        """Render key events as horizontal timeline (height=300).

        Timeline shows 5-10 critical events with timestamps.
        Each event is a circle on the timeline with description below.
        """
        sw, _ = surface.get_size()
        timeline_y = MARGIN + BANNER_HEIGHT + MARGIN

        # Section title
        title_surf = self._font_normal.render("KEY EVENTS TIMELINE", True, HIGHLIGHT_COLOR)
        surface.blit(title_surf, (MARGIN, timeline_y))
        draw.line(
            surface,
            BORDER_COLOR,
            (MARGIN, timeline_y + 24),
            (sw - MARGIN, timeline_y + 24),
            1,
        )

        # Filter to display at most 10 events (sorted by timestamp)
        events = sorted(battle_result.events, key=lambda e: e.timestamp)[:10]

        if not events:
            no_data = self._font_small.render("No key events recorded", True, TEXT_COLOR)
            surface.blit(no_data, (MARGIN + 10, timeline_y + 40))
            return

        # Timeline horizontal line
        line_y = timeline_y + 60
        line_start_x = MARGIN + 20
        line_end_x = sw - MARGIN - 20
        draw.line(
            surface,
            BORDER_COLOR,
            (line_start_x, line_y),
            (line_end_x, line_y),
            2,
        )

        # Calculate event positions
        max_timestamp = max(e.timestamp for e in events) if events else 1.0
        max_timestamp = max(max_timestamp, 1.0)  # avoid division by zero
        line_width = line_end_x - line_start_x

        for i, event in enumerate(events):
            # Position on timeline
            x_ratio = event.timestamp / max_timestamp if max_timestamp > 0 else 0.5
            event_x = line_start_x + int(line_width * x_ratio)

            # Event circle (color by event type)
            circle_color = self._event_color(event.event_type)
            draw.circle(surface, circle_color, (event_x, line_y), 6)
            draw.circle(surface, BORDER_COLOR, (event_x, line_y), 6, 1)

            # Timestamp label above
            time_label = self._font_small.render(f"{event.timestamp:.0f}s", True, HIGHLIGHT_COLOR)
            surface.blit(time_label, (event_x - time_label.get_width() // 2, line_y - 20))

            # Description below (alternating up/down to avoid overlap)
            desc_y = line_y + 12 + (i % 3) * 16
            desc_text = event.description or event.event_type
            if len(desc_text) > 40:
                desc_text = desc_text[:37] + "..."
            desc_surf = self._font_small.render(desc_text, True, TEXT_COLOR)
            surface.blit(desc_surf, (event_x - desc_surf.get_width() // 2, desc_y))

    @staticmethod
    def _event_color(event_type: str) -> tuple[int, int, int]:
        """Return color for event type."""
        if event_type in ("unit_killed", "building_destroyed"):
            return DEFEAT_COLOR
        if event_type == "morale_break":
            return HIGHLIGHT_COLOR
        if event_type == "vl_capture":
            return COMPLETED_COLOR
        return TEXT_COLOR

    # ========================================================================
    # MVP unit rendering
    # ========================================================================

    def _render_mvp_unit(self, surface: Surface, battle_result: BattleResult) -> None:
        """Render MVP unit showcase at the bottom (height=200).

        Shows the MVP unit's icon, name, key stats, and achievements.
        Uses ``calculate_mvp()`` if ``mvp_unit_id`` is None.
        """
        sw, sh = surface.get_size()
        mvp_y = sh - MARGIN - MVP_HEIGHT

        # Background panel
        draw.rect(surface, PANEL_COLOR, Rect(MARGIN, mvp_y, sw - 2 * MARGIN, MVP_HEIGHT))
        draw.rect(surface, BORDER_COLOR, Rect(MARGIN, mvp_y, sw - 2 * MARGIN, MVP_HEIGHT), 1)

        # Section title
        title_surf = self._font_normal.render("MVP UNIT", True, HIGHLIGHT_COLOR)
        surface.blit(title_surf, (MARGIN + 10, mvp_y + 8))
        draw.line(
            surface,
            BORDER_COLOR,
            (MARGIN, mvp_y + 28),
            (sw - MARGIN, mvp_y + 28),
            1,
        )

        # Determine MVP unit
        mvp_id = battle_result.mvp_unit_id
        if mvp_id is None:
            mvp_id = calculate_mvp(battle_result.unit_records)

        if mvp_id is None:
            no_mvp = self._font_small.render("No MVP data available", True, TEXT_COLOR)
            surface.blit(no_mvp, (MARGIN + 10, mvp_y + 40))
            return

        # Find MVP unit record
        mvp_record = next(
            (r for r in battle_result.unit_records if r.unit_id == mvp_id),
            None,
        )

        if mvp_record is None:
            no_mvp = self._font_small.render(
                f"MVP: {mvp_id} (details unavailable)",
                True,
                TEXT_COLOR,
            )
            surface.blit(no_mvp, (MARGIN + 10, mvp_y + 40))
            return

        # Render MVP details
        self._render_mvp_details(surface, mvp_record, mvp_y + 40)

    def _render_mvp_details(
        self,
        surface: Surface,
        record: UnitBattleRecord,
        y_start: int,
    ) -> None:
        """Render MVP unit details (name, stats, achievements)."""
        sw, _ = surface.get_size()

        # Unit name (large)
        name_surf = self._font_normal.render(
            f"{record.unit_id} ({record.unit_type})",
            True,
            HIGHLIGHT_COLOR,
        )
        surface.blit(name_surf, (MARGIN + 10, y_start))

        # Faction badge
        faction_color = VICTORY_COLOR if record.faction == "allies" else DEFEAT_COLOR
        faction_surf = self._font_small.render(
            record.faction.upper(),
            True,
            faction_color,
        )
        surface.blit(faction_surf, (MARGIN + 10 + name_surf.get_width() + 12, y_start + 4))

        # Stats row
        stats_y = y_start + 28
        stats = [
            f"Kills: {record.kills}",
            f"Damage: {record.damage_dealt:.0f}",
            f"Accuracy: {record.efficiency:.0%}",
            f"Shots: {record.shots_fired}",
            f"Hits: {record.shots_hit}",
        ]
        if record.survived:
            stats.append("Survived ✓")
        else:
            stats.append("KIA ✗")

        stat_x = MARGIN + 10
        for stat in stats:
            stat_surf = self._font_small.render(stat, True, TEXT_COLOR)
            surface.blit(stat_surf, (stat_x, stats_y))
            stat_x += stat_surf.get_width() + 24
            if stat_x > sw - MARGIN - 100:
                break

        # Achievements row (based on performance)
        ach_y = stats_y + 22
        achievements = self._compute_achievements(record)
        if achievements:
            for i, ach in enumerate(achievements):
                ach_surf = self._font_small.render(f"★ {ach}", True, COMPLETED_COLOR)
                surface.blit(ach_surf, (MARGIN + 10 + i * 200, ach_y))

    @staticmethod
    def _compute_achievements(record: UnitBattleRecord) -> list[str]:
        """Compute achievement badges for the MVP unit."""
        achievements: list[str] = []
        if record.kills >= 5:
            achievements.append("Ace (5+ kills)")
        elif record.kills >= 3:
            achievements.append("Veteran (3+ kills)")
        if record.efficiency >= 0.8 and record.shots_fired >= 10:
            achievements.append("Sharpshooter (80%+ acc)")
        if record.survived:
            achievements.append("Survivor")
        if record.damage_dealt >= 200:
            achievements.append("Heavy Hitter (200+ dmg)")
        return achievements


__all__ = [
    "PostBattleReportRenderer",
    "BattleEvent",
    "calculate_mvp",
    "DEFAULT_BATTLE_DURATION_SECONDS",
    "MVP_WEIGHT_HIT_RATE",
    "MVP_WEIGHT_KILLS",
    "MVP_WEIGHT_SURVIVAL",
]
