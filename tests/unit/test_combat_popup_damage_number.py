"""V-13 (Wave D6): Unit tests for damage number display in CombatPopupManager.

Tests cover 6 dimensions (Happy/Error/Boundary/Performance/Config/Integration):
1. Constants (Wave B-rev spec values)
2. _get_damage_color() module helper (DamageType → color mapping)
3. add_damage_number() happy path (popup creation, field correctness)
4. Throttling (200ms per-unit, no-throttle when unit_id=None)
5. Critical override (is_critical param overrides damage.is_critical)
6. FIFO eviction (MAX_DAMAGE_NUMBERS=10)
7. Font caching (_get_font with normal/damage-number modes)
8. Render integration (no crash, font selection)
9. Coexistence with add_popup (max_popups overall limit)
10. Performance (1000 calls < 100ms)
"""

from __future__ import annotations

import os
import time

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame  # noqa: E402

pygame.init()

import pytest  # noqa: E402

from pycc2.domain.value_objects.damage import Damage, DamageType  # noqa: E402
from pycc2.presentation.ui.combat_popup import (  # noqa: E402
    DAMAGE_COLOR_CRITICAL,
    DAMAGE_COLOR_DEFAULT,
    DAMAGE_COLOR_EXPLOSIVE,
    DAMAGE_COLOR_INCENDIARY,
    DAMAGE_COLOR_KINETIC,
    DAMAGE_NUMBER_FONT_SIZE_CRITICAL,
    DAMAGE_NUMBER_FONT_SIZE_NORMAL,
    DAMAGE_NUMBER_LIFETIME_MS,
    DAMAGE_NUMBER_THROTTLE_MS,
    MAX_DAMAGE_NUMBERS,
    CombatPopupManager,
    _get_damage_color,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture()
def manager(pygame_display):
    """Create a CombatPopupManager instance for testing."""
    return CombatPopupManager(max_popups=20)


@pytest.fixture()
def kinetic_damage():
    """Create a kinetic damage instance (non-critical)."""
    return Damage(amount=25.0, damage_type=DamageType.KINETIC)


@pytest.fixture()
def explosive_damage():
    """Create an explosive damage instance."""
    return Damage(amount=40.0, damage_type=DamageType.EXPLOSIVE)


@pytest.fixture()
def incendiary_damage():
    """Create an incendiary damage instance."""
    return Damage(amount=30.0, damage_type=DamageType.INCENDIARY)


@pytest.fixture()
def critical_damage():
    """Create a critical (>=75) kinetic damage instance."""
    return Damage(amount=80.0, damage_type=DamageType.KINETIC)


@pytest.fixture()
def fragmentation_damage():
    """Create a fragmentation damage instance (default color branch)."""
    return Damage(amount=20.0, damage_type=DamageType.FRAGMENTATION)


# ============================================================================
# 1. Constants (Wave B-rev spec values)
# ============================================================================


class TestConstants:
    """Verify V-13 constants match Wave B-rev specification."""

    def test_max_damage_numbers_is_10(self):
        """MAX_DAMAGE_NUMBERS = 10 (FIFO eviction threshold)."""
        assert MAX_DAMAGE_NUMBERS == 10

    def test_throttle_ms_is_200(self):
        """DAMAGE_NUMBER_THROTTLE_MS = 200.0 (same-unit suppression window)."""
        assert DAMAGE_NUMBER_THROTTLE_MS == 200.0

    def test_lifetime_ms_is_1200(self):
        """DAMAGE_NUMBER_LIFETIME_MS = 1200.0 (1.2s display duration)."""
        assert DAMAGE_NUMBER_LIFETIME_MS == 1200.0

    def test_font_size_normal_is_18(self):
        """DAMAGE_NUMBER_FONT_SIZE_NORMAL = 18."""
        assert DAMAGE_NUMBER_FONT_SIZE_NORMAL == 18

    def test_font_size_critical_is_24(self):
        """DAMAGE_NUMBER_FONT_SIZE_CRITICAL = 24 (larger for crits)."""
        assert DAMAGE_NUMBER_FONT_SIZE_CRITICAL == 24

    def test_critical_color_is_red(self):
        """DAMAGE_COLOR_CRITICAL = (255, 80, 80) red."""
        assert DAMAGE_COLOR_CRITICAL == (255, 80, 80)

    def test_explosive_color_is_orange(self):
        """DAMAGE_COLOR_EXPLOSIVE = (255, 150, 30) orange."""
        assert DAMAGE_COLOR_EXPLOSIVE == (255, 150, 30)

    def test_incendiary_color_is_yellow(self):
        """DAMAGE_COLOR_INCENDIARY = (255, 200, 50) yellow."""
        assert DAMAGE_COLOR_INCENDIARY == (255, 200, 50)

    def test_kinetic_color_is_white(self):
        """DAMAGE_COLOR_KINETIC = (255, 255, 255) white."""
        assert DAMAGE_COLOR_KINETIC == (255, 255, 255)

    def test_default_color_is_light_gray(self):
        """DAMAGE_COLOR_DEFAULT = (220, 220, 220) light gray."""
        assert DAMAGE_COLOR_DEFAULT == (220, 220, 220)


# ============================================================================
# 2. _get_damage_color() module helper
# ============================================================================


class TestGetDamageColor:
    """Test the _get_damage_color() module-private function."""

    def test_critical_overrides_type_color(self, critical_damage):
        """Critical hit always returns red, regardless of damage type."""
        color = _get_damage_color(critical_damage.damage_type, is_critical=True)
        assert color == DAMAGE_COLOR_CRITICAL

    def test_kinetic_returns_white(self, kinetic_damage):
        """Non-critical kinetic damage returns white."""
        color = _get_damage_color(kinetic_damage.damage_type, is_critical=False)
        assert color == DAMAGE_COLOR_KINETIC

    def test_explosive_returns_orange(self, explosive_damage):
        """Non-critical explosive damage returns orange."""
        color = _get_damage_color(explosive_damage.damage_type, is_critical=False)
        assert color == DAMAGE_COLOR_EXPLOSIVE

    def test_incendiary_returns_yellow(self, incendiary_damage):
        """Non-critical incendiary damage returns yellow."""
        color = _get_damage_color(incendiary_damage.damage_type, is_critical=False)
        assert color == DAMAGE_COLOR_INCENDIARY

    def test_fragmentation_returns_default(self, fragmentation_damage):
        """Fragmentation damage (no specific color) returns default light gray."""
        color = _get_damage_color(fragmentation_damage.damage_type, is_critical=False)
        assert color == DAMAGE_COLOR_DEFAULT

    def test_crushing_returns_default(self):
        """Crushing damage returns default (not in color map)."""
        color = _get_damage_color(DamageType.CRUSHING, is_critical=False)
        assert color == DAMAGE_COLOR_DEFAULT

    def test_critical_with_explosive_still_red(self, explosive_damage):
        """Critical explosive damage still returns red (critical overrides)."""
        color = _get_damage_color(explosive_damage.damage_type, is_critical=True)
        assert color == DAMAGE_COLOR_CRITICAL


# ============================================================================
# 3. add_damage_number() happy path
# ============================================================================


class TestAddDamageNumberHappyPath:
    """Test add_damage_number() successful display."""

    def test_returns_true_when_displayed(self, manager, kinetic_damage):
        """add_damage_number() returns True when damage is displayed."""
        result = manager.add_damage_number((100, 200), kinetic_damage)
        assert result is True

    def test_creates_popup_in_queue(self, manager, kinetic_damage):
        """Damage popup is added to the popup queue."""
        manager.add_damage_number((100, 200), kinetic_damage)
        assert len(manager._popups) == 1

    def test_popup_has_correct_text(self, manager, kinetic_damage):
        """Popup text is formatted as '-N' (e.g. '-25')."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.text == "-25"

    def test_popup_has_correct_position(self, manager, kinetic_damage):
        """Popup position matches target_position argument."""
        manager.add_damage_number((150.5, 250.3), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.x == 150.5
        assert popup.y == 250.3

    def test_popup_marks_is_damage_number(self, manager, kinetic_damage):
        """Popup has is_damage_number=True flag."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.is_damage_number is True

    def test_popup_stores_damage_amount(self, manager, kinetic_damage):
        """Popup stores the original damage amount."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.damage_amount == 25.0

    def test_popup_stores_damage_type_name(self, manager, kinetic_damage):
        """Popup stores damage type name as string."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.damage_type_name == "KINETIC"

    def test_popup_duration_matches_lifetime_ms(self, manager, kinetic_damage):
        """Popup duration is DAMAGE_NUMBER_LIFETIME_MS / 1000 (1.2s)."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.duration == pytest.approx(1.2)

    def test_popup_color_matches_damage_type(self, manager, kinetic_damage):
        """Non-critical popup color matches damage type color (white for kinetic)."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.color == DAMAGE_COLOR_KINETIC

    def test_popup_font_size_normal_for_non_critical(self, manager, kinetic_damage):
        """Non-critical popup uses normal font size (18)."""
        manager.add_damage_number((100, 200), kinetic_damage)
        popup = manager._popups[-1]
        assert popup.font_size == DAMAGE_NUMBER_FONT_SIZE_NORMAL

    def test_popup_truncates_amount_to_int(self, manager):
        """Damage amount 25.7 is displayed as '-25' (int truncation)."""
        damage = Damage(amount=25.7, damage_type=DamageType.KINETIC)
        manager.add_damage_number((100, 200), damage)
        popup = manager._popups[-1]
        assert popup.text == "-25"
        assert popup.damage_amount == 25.7  # Original float preserved


# ============================================================================
# 4. Throttling (200ms per-unit)
# ============================================================================


class TestThrottling:
    """Test 200ms per-unit throttle logic."""

    def test_same_unit_within_200ms_suppressed(self, manager, kinetic_damage):
        """Second call within 200ms for same unit_id returns False."""
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        # Immediate second call should be throttled
        result = manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        assert result is False

    def test_same_unit_within_200ms_no_new_popup(self, manager, kinetic_damage):
        """Throttled call does not add a new popup."""
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        assert len(manager._popups) == 1

    def test_different_units_not_throttled(self, manager, kinetic_damage):
        """Different unit_ids are not throttled against each other."""
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_2")
        assert len(manager._popups) == 2

    def test_no_unit_id_no_throttle(self, manager, kinetic_damage):
        """Calls without unit_id are never throttled."""
        manager.add_damage_number((100, 200), kinetic_damage, unit_id=None)
        manager.add_damage_number((100, 200), kinetic_damage, unit_id=None)
        manager.add_damage_number((100, 200), kinetic_damage, unit_id=None)
        assert len(manager._popups) == 3

    def test_throttle_after_window_expires(self, manager, kinetic_damage, monkeypatch):
        """After 200ms window, same unit can be displayed again."""
        # First call at t=0
        current_time = [0.0]
        monkeypatch.setattr(
            "pycc2.presentation.ui.combat_popup.time.time",
            lambda: current_time[0],
        )
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")

        # Move time forward past throttle window (201ms)
        current_time[0] = 0.201
        result = manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        assert result is True
        assert len(manager._popups) == 2

    def test_throttle_exact_boundary_200ms(self, manager, kinetic_damage, monkeypatch):
        """At exactly 200ms boundary, throttle does NOT apply (uses <, not <=)."""
        current_time = [0.0]
        monkeypatch.setattr(
            "pycc2.presentation.ui.combat_popup.time.time",
            lambda: current_time[0],
        )
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")

        # Exactly 200ms (0.2s) - NOT throttled because check is < 200ms (strict less-than)
        current_time[0] = 0.2
        result = manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        assert result is True
        assert len(manager._popups) == 2

    def test_throttle_just_below_boundary_199ms(self, manager, kinetic_damage, monkeypatch):
        """At 199ms (just below boundary), throttle applies."""
        current_time = [0.0]
        monkeypatch.setattr(
            "pycc2.presentation.ui.combat_popup.time.time",
            lambda: current_time[0],
        )
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")

        # 199ms - should be throttled (< 200ms)
        current_time[0] = 0.199
        result = manager.add_damage_number((100, 200), kinetic_damage, unit_id="unit_1")
        assert result is False
        assert len(manager._popups) == 1


# ============================================================================
# 5. Critical override
# ============================================================================


class TestCriticalOverride:
    """Test is_critical parameter overriding damage.is_critical."""

    def test_critical_damage_uses_critical_color(self, manager, critical_damage):
        """Damage with amount >= 75 uses critical red color."""
        manager.add_damage_number((100, 200), critical_damage)
        popup = manager._popups[-1]
        assert popup.color == DAMAGE_COLOR_CRITICAL

    def test_critical_damage_uses_larger_font(self, manager, critical_damage):
        """Critical damage uses DAMAGE_NUMBER_FONT_SIZE_CRITICAL (24)."""
        manager.add_damage_number((100, 200), critical_damage)
        popup = manager._popups[-1]
        assert popup.font_size == DAMAGE_NUMBER_FONT_SIZE_CRITICAL

    def test_critical_damage_text_has_exclamation(self, manager, critical_damage):
        """Critical damage text ends with '!' (e.g. '-80!')."""
        manager.add_damage_number((100, 200), critical_damage)
        popup = manager._popups[-1]
        assert popup.text == "-80!"

    def test_explicit_critical_true_overrides_non_critical_damage(self, manager, kinetic_damage):
        """is_critical=True overrides damage.is_critical=False."""
        result = manager.add_damage_number(
            (100, 200), kinetic_damage, is_critical=True
        )
        assert result is True
        popup = manager._popups[-1]
        assert popup.color == DAMAGE_COLOR_CRITICAL
        assert popup.font_size == DAMAGE_NUMBER_FONT_SIZE_CRITICAL
        assert popup.text == "-25!"

    def test_explicit_critical_false_overrides_critical_damage(self, manager, critical_damage):
        """is_critical=False overrides damage.is_critical=True."""
        result = manager.add_damage_number(
            (100, 200), critical_damage, is_critical=False
        )
        assert result is True
        popup = manager._popups[-1]
        # Should use kinetic color (white), not critical red
        assert popup.color == DAMAGE_COLOR_KINETIC
        assert popup.font_size == DAMAGE_NUMBER_FONT_SIZE_NORMAL
        assert popup.text == "-80"  # No exclamation

    def test_explicit_none_uses_damage_property(self, manager, kinetic_damage):
        """is_critical=None (default) uses damage.is_critical property."""
        result = manager.add_damage_number(
            (100, 200), kinetic_damage, is_critical=None
        )
        assert result is True
        popup = manager._popups[-1]
        # kinetic_damage.amount=25, is_critical=False (amount < 75)
        assert popup.color == DAMAGE_COLOR_KINETIC
        assert popup.font_size == DAMAGE_NUMBER_FONT_SIZE_NORMAL


# ============================================================================
# 6. FIFO eviction
# ============================================================================


class TestFifoEviction:
    """Test FIFO eviction when exceeding MAX_DAMAGE_NUMBERS."""

    def test_can_add_up_to_max_damage_numbers(self, manager):
        """Can add exactly MAX_DAMAGE_NUMBERS (10) damage popups without eviction."""
        for i in range(MAX_DAMAGE_NUMBERS):
            damage = Damage(amount=10.0 + i, damage_type=DamageType.KINETIC)
            # Use unique unit_id to avoid throttle
            manager.add_damage_number((100, 200), damage, unit_id=f"unit_{i}")
        damage_popups = [p for p in manager._popups if p.is_damage_number]
        assert len(damage_popups) == MAX_DAMAGE_NUMBERS

    def test_eviction_removes_oldest_damage_popup(self, manager):
        """When exceeding MAX_DAMAGE_NUMBERS, oldest damage popup is removed."""
        # Add 11 damage numbers with unique unit_ids
        for i in range(MAX_DAMAGE_NUMBERS + 1):
            damage = Damage(amount=10.0 + i, damage_type=DamageType.KINETIC)
            manager.add_damage_number((100, 200), damage, unit_id=f"unit_{i}")

        damage_popups = [p for p in manager._popups if p.is_damage_number]
        # Should have exactly MAX_DAMAGE_NUMBERS (oldest evicted)
        assert len(damage_popups) == MAX_DAMAGE_NUMBERS
        # First popup (amount=10.0, text="-10") should have been evicted
        assert all(p.text != "-10" for p in damage_popups)

    def test_eviction_preserves_non_damage_popups(self, manager):
        """FIFO eviction only removes damage popups, not regular popups."""
        # Add a regular popup first
        manager.add_popup("Taking fire!", 100, 200)
        # Now add MAX_DAMAGE_NUMBERS damage popups
        for i in range(MAX_DAMAGE_NUMBERS):
            damage = Damage(amount=10.0 + i, damage_type=DamageType.KINETIC)
            manager.add_damage_number((100, 200), damage, unit_id=f"unit_{i}")

        # Regular popup should still be there
        regular_popups = [p for p in manager._popups if not p.is_damage_number]
        assert len(regular_popups) == 1
        assert regular_popups[0].text == "Taking fire!"


# ============================================================================
# 7. Font caching (_get_font)
# ============================================================================


class TestFontCaching:
    """Test _get_font() caching behavior."""

    def test_normal_popup_uses_default_font_size(self, manager):
        """Non-damage-number popups use font size 13 (default)."""
        # Trigger font init via add_popup (non-damage)
        manager.add_popup("Test", 100, 200)
        font = manager._get_font(13, is_damage_number=False)
        assert isinstance(font, pygame.font.Font)

    def test_damage_number_uses_cached_font(self, manager, kinetic_damage):
        """Damage number font is cached by size after render()."""
        manager.add_damage_number((100, 200), kinetic_damage)
        # Trigger render to populate font cache
        surface = pygame.Surface((800, 600))

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        manager.render(surface, FakeCamera())
        # Font for size 18 should be in cache after render
        assert DAMAGE_NUMBER_FONT_SIZE_NORMAL in manager._damage_fonts

    def test_critical_uses_separate_font_size(self, manager, critical_damage):
        """Critical hit uses different font size (24), cached separately after render."""
        manager.add_damage_number((100, 200), critical_damage)
        surface = pygame.Surface((800, 600))

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        manager.render(surface, FakeCamera())
        assert DAMAGE_NUMBER_FONT_SIZE_CRITICAL in manager._damage_fonts

    def test_font_cache_reuses_same_object(self, manager, kinetic_damage):
        """Calling _get_font twice with same size returns same Font object."""
        manager.add_damage_number((100, 200), kinetic_damage)
        font1 = manager._get_font(DAMAGE_NUMBER_FONT_SIZE_NORMAL, is_damage_number=True)
        font2 = manager._get_font(DAMAGE_NUMBER_FONT_SIZE_NORMAL, is_damage_number=True)
        assert font1 is font2

    def test_returns_valid_font_object(self, manager):
        """_get_font always returns a usable Font object (never None)."""
        font = manager._get_font(18, is_damage_number=True)
        assert isinstance(font, pygame.font.Font)
        # Verify font can render text
        surface = font.render("test", True, (255, 255, 255))
        assert surface.get_size()[0] > 0


# ============================================================================
# 8. Render integration
# ============================================================================


class TestRenderIntegration:
    """Test render() integration with damage numbers."""

    def test_render_with_damage_number_no_crash(self, manager, kinetic_damage):
        """render() does not crash with damage number popups."""

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        manager.add_damage_number((100, 200), kinetic_damage)
        surface = pygame.Surface((800, 600))
        manager.render(surface, FakeCamera())

    def test_render_with_critical_damage_no_crash(self, manager, critical_damage):
        """render() handles critical damage popups (larger font) without crash."""

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        manager.add_damage_number((100, 200), critical_damage)
        surface = pygame.Surface((800, 600))
        manager.render(surface, FakeCamera())

    def test_render_mixed_popups_no_crash(self, manager, kinetic_damage):
        """render() handles mix of regular + damage popups."""

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        manager.add_popup("Taking fire!", 100, 200)
        manager.add_damage_number((150, 250), kinetic_damage)
        manager.add_popup("Pinned!", 200, 300)
        surface = pygame.Surface((800, 600))
        manager.render(surface, FakeCamera())

    def test_render_empty_queue_no_crash(self, manager):
        """render() with empty popup queue returns without error."""

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        surface = pygame.Surface((800, 600))
        manager.render(surface, FakeCamera())


# ============================================================================
# 9. Coexistence with add_popup (max_popups overall limit)
# ============================================================================


class TestCoexistenceWithRegularPopups:
    """Test damage numbers coexist with regular popups."""

    def test_damage_and_regular_popups_coexist(self, manager, kinetic_damage):
        """Both damage and regular popups can coexist in queue."""
        manager.add_popup("Taking fire!", 100, 200)
        manager.add_damage_number((150, 250), kinetic_damage, unit_id="u1")
        manager.add_popup("Pinned!", 200, 300)
        assert len(manager._popups) == 3

    def test_overall_max_popups_enforced(self, kinetic_damage):
        """Overall max_popups limit is enforced (mix of regular + damage)."""
        mgr = CombatPopupManager(max_popups=5)
        # Add 3 regular + 3 damage = 6 total, should cap at 5
        for i in range(3):
            mgr.add_popup(f"Popup {i}", 100 + i * 10, 200)
        for i in range(3):
            damage = Damage(amount=10.0 + i, damage_type=DamageType.KINETIC)
            mgr.add_damage_number(
                (100 + i * 10, 200), damage, unit_id=f"unit_{i}"
            )
        assert len(mgr._popups) <= 5

    def test_damage_popup_does_not_crash_regular_render(self, manager, kinetic_damage):
        """Regular render() pipeline handles damage popups without error."""
        manager.add_damage_number((100, 200), kinetic_damage, unit_id="u1")
        manager.add_popup("Test", 150, 250)

        class FakeCamera:
            offset_x = 10
            offset_y = 20

        surface = pygame.Surface((800, 600))
        manager.render(surface, FakeCamera())


# ============================================================================
# 10. Performance
# ============================================================================


class TestPerformance:
    """Performance benchmarks for damage number display."""

    def test_1000_add_calls_under_100ms(self):
        """1000 add_damage_number calls should complete under 100ms."""
        mgr = CombatPopupManager(max_popups=1000)
        damage = Damage(amount=25.0, damage_type=DamageType.KINETIC)

        start = time.perf_counter()
        for i in range(1000):
            mgr.add_damage_number(
                (100.0, 200.0), damage, unit_id=f"unit_{i}"
            )
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 100.0, f"1000 calls took {elapsed_ms:.1f}ms"

    def test_render_with_50_popups_under_50ms(self, kinetic_damage):
        """render() with 50 damage popups should complete under 50ms."""
        mgr = CombatPopupManager(max_popups=50)
        for i in range(50):
            damage = Damage(amount=10.0 + i, damage_type=DamageType.KINETIC)
            mgr.add_damage_number(
                (100.0 + i, 200.0 + i), damage, unit_id=f"unit_{i}"
            )

        class FakeCamera:
            offset_x = 0
            offset_y = 0

        surface = pygame.Surface((800, 600))

        start = time.perf_counter()
        mgr.render(surface, FakeCamera())
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        assert elapsed_ms < 50.0, f"Render took {elapsed_ms:.1f}ms"
