"""Unit tests for TriggerSystem (MC2-02): once / cooldown / condition gating."""

from __future__ import annotations

from pycc2.services.trigger_system import Trigger, TriggerSystem


def _recording_action(name: str, sink: list[str]):
    def _action(state) -> None:
        sink.append(name)

    return _action


class TestTriggerSystemTick:
    def test_condition_met_fires_and_returns_id(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="t1", condition=lambda s: s["on"], action=_recording_action("t1", sink)
            )
        )
        assert system.tick({"on": True}) == ["t1"]
        assert sink == ["t1"]

    def test_condition_not_met_does_not_fire(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="t1", condition=lambda s: s["on"], action=_recording_action("t1", sink)
            )
        )
        assert system.tick({"on": False}) == []
        assert sink == []
        assert system.list_triggers() == [("t1", 0, None)]

    def test_condition_rechecked_every_tick(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="t1", condition=lambda s: s["on"], action=_recording_action("t1", sink)
            )
        )
        assert system.tick({"on": True}) == ["t1"]
        assert system.tick({"on": False}) == []
        assert system.tick({"on": True}) == ["t1"]
        assert sink == ["t1", "t1"]


class TestTriggerOnce:
    def test_once_fires_exactly_once(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="once_t",
                condition=lambda _s: True,
                action=_recording_action("once_t", sink),
                once=True,
            )
        )
        assert system.tick({}) == ["once_t"]
        assert system.tick({}) == []
        assert system.tick({}) == []
        assert sink == ["once_t"]
        assert system.list_triggers() == [("once_t", 1, 1)]

    def test_non_once_never_gated(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="always", condition=lambda _s: True, action=_recording_action("a", sink)
            )
        )
        for _ in range(3):
            assert system.tick({}) == ["always"]
        assert sink == ["a", "a", "a"]


class TestTriggerCooldown:
    def test_cooldown_suppresses_then_refires(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="cd",
                condition=lambda _s: True,
                action=_recording_action("cd", sink),
                cooldown_ticks=3,
            )
        )
        assert system.tick({}) == ["cd"]  # tick 1: fire
        assert system.tick({}) == []  # tick 2: 2-1 < 3 → suppressed
        assert system.tick({}) == []  # tick 3: 3-1 < 3 → suppressed
        assert system.tick({}) == ["cd"]  # tick 4: 4-1 >= 3 → fire
        assert sink == ["cd", "cd"]

    def test_zero_cooldown_fires_every_tick(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="zero",
                condition=lambda _s: True,
                action=_recording_action("z", sink),
                cooldown_ticks=0,
            )
        )
        assert system.tick({}) == ["zero"]
        assert system.tick({}) == ["zero"]
        assert sink == ["z", "z"]


class TestTriggerObservability:
    def test_list_triggers_reports_counts_and_last_tick(self):
        system = TriggerSystem()
        system.register(Trigger(trigger_id="a", condition=lambda _s: True, action=lambda _s: None))
        system.register(Trigger(trigger_id="b", condition=lambda _s: False, action=lambda _s: None))
        system.tick({})
        system.tick({})
        assert system.list_triggers() == [("a", 2, 2), ("b", 0, None)]

    def test_registration_order_is_evaluation_order(self):
        order: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="first",
                condition=lambda _s: True,
                action=lambda _s: order.append("first"),
            )
        )
        system.register(
            Trigger(
                trigger_id="second",
                condition=lambda _s: True,
                action=lambda _s: order.append("second"),
            )
        )
        assert system.tick({}) == ["first", "second"]
        assert order == ["first", "second"]

    def test_group_filtering(self):
        sink: list[str] = []
        system = TriggerSystem()
        system.register(
            Trigger(
                trigger_id="log",
                group="logistics",
                condition=lambda _s: True,
                action=_recording_action("log", sink),
            )
        )
        system.register(
            Trigger(
                trigger_id="scen",
                group="scenario",
                condition=lambda _s: True,
                action=_recording_action("scen", sink),
            )
        )
        assert system.tick({}, group="logistics") == ["log"]
        assert system.tick({}, group="scenario") == ["scen"]
        assert system.tick({}) == ["log", "scen"]
        assert sink == ["log", "scen", "log", "scen"]
