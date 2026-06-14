from pycc2.presentation.ui.hint_manager import HintManager, HINTS


class TestHintManagerDefaultState:
    def test_default_state(self):
        mgr = HintManager()
        assert mgr.enabled is True
        assert len(mgr._hints) == 0
        assert mgr._global_cooldown == 0


class TestHintManagerShowHide:
    def test_show_hint_adds_to_list(self):
        mgr = HintManager()
        mgr.show_hint("test", 100, 200)
        assert len(mgr._hints) == 1
        assert mgr._hints[0].text == "test"
        assert mgr._hints[0].x == 100
        assert mgr._hints[0].y == 200

    def test_show_hint_disabled_does_not_add(self):
        mgr = HintManager()
        mgr.set_enabled(False)
        mgr.show_hint("test", 100, 200)
        assert len(mgr._hints) == 0

    def test_set_enabled_false_clears_hints(self):
        mgr = HintManager()
        mgr.show_hint("a", 10, 20)
        mgr.show_hint("b", 30, 40)
        assert len(mgr._hints) == 2
        mgr.set_enabled(False)
        assert len(mgr._hints) == 0
        assert mgr.enabled is False


class TestHintManagerLifetimeDecay:
    def test_lifetime_decay(self):
        mgr = HintManager()
        mgr.show_hint("decay", 50, 60, lifetime=5)
        assert mgr._hints[0].lifetime == 5
        for _ in range(3):
            mgr.update()
        assert mgr._hints[0].lifetime == 2

    def test_hint_removed_when_expired(self):
        mgr = HintManager()
        mgr.show_hint("short", 0, 0, lifetime=2)
        mgr.update()
        assert len(mgr._hints) == 1
        mgr.update()
        assert len(mgr._hints) == 0


class TestHintManagerCooldown:
    def test_cooldown_initially_zero(self):
        mgr = HintManager()
        assert mgr._global_cooldown == 0


class TestHintsDictionary:
    def test_all_hints_defined(self):
        required = {
            "first_select",
            "right_click_move",
            "right_click_attack",
            "low_hp",
            "out_of_ammo",
            "enemy_commander_spotted",
        }
        assert set(HINTS.keys()) == required

    def test_hint_values_are_tuples(self):
        for key, val in HINTS.items():
            assert isinstance(val, tuple), f"HINTS['{key}'] is not a tuple"
            assert len(val) == 3, f"HINTS['{key}'] should have 3 elements"


class TestMaxHintsLimit:
    def test_multiple_hints_can_coexist(self):
        mgr = HintManager()
        for i in range(10):
            mgr.show_hint(f"hint{i}", i * 10, i * 10)
        assert len(mgr._hints) == 10
