from __future__ import annotations

from pycc2.services.event_bus import EventBus
from pycc2.services.event_protocol import MoraleChanged, UnitMoved


class TestSubscribeUnsubscribe:
    def test_subscribe_and_receive(self):
        bus = EventBus()
        received: list[UnitMoved] = []

        def handler(e: UnitMoved):
            received.append(e)

        bus.subscribe(UnitMoved, handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert len(received) == 1
        assert received[0]["unit_id"] == "u1"

    def test_unsubscribe_stops_receiving(self):
        bus = EventBus()
        received: list[UnitMoved] = []

        def handler(e: UnitMoved):
            received.append(e)

        bus.subscribe(UnitMoved, handler)
        bus.unsubscribe(UnitMoved, handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert len(received) == 0

    def test_unsubscribe_returns_true_when_found(self):
        bus = EventBus()

        def handler(e: UnitMoved):
            pass

        bus.subscribe(UnitMoved, handler)
        assert bus.unsubscribe(UnitMoved, handler) is True

    def test_unsubscribe_returns_false_when_not_found(self):
        bus = EventBus()

        def handler(e: UnitMoved):
            pass

        assert bus.unsubscribe(UnitMoved, handler) is False


class TestPublish:
    def test_publish_to_multiple_handlers(self):
        bus = EventBus()
        results: list[int] = []

        def handler_a(e: UnitMoved):
            results.append(1)

        def handler_b(e: UnitMoved):
            results.append(2)

        bus.subscribe(UnitMoved, handler_a)
        bus.subscribe(UnitMoved, handler_b)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert sorted(results) == [1, 2]


class TestEventTypeIsolation:
    def test_unit_moved_handler_does_not_receive_morale_changed(self):
        bus = EventBus()
        received: list[UnitMoved] = []

        def handler(e: UnitMoved):
            received.append(e)

        bus.subscribe(UnitMoved, handler)
        morale_event: MoraleChanged = {
            "unit_id": "u1",
            "old_value": 80,
            "new_value": 60,
            "event_type": "casualty",
            "state_changed": True,
        }
        bus.publish(morale_event)
        assert len(received) == 0


class TestEnqueueAndProcessQueue:
    def test_enqueue_delays_processing(self):
        bus = EventBus()
        received: list[UnitMoved] = []

        def handler(e: UnitMoved):
            received.append(e)

        bus.subscribe(UnitMoved, handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.enqueue(event)
        assert len(received) == 0
        count = bus.process_queue()
        assert count == 1
        assert len(received) == 1

    def test_process_queue_returns_count(self):
        bus = EventBus()

        def handler(e: UnitMoved):
            pass

        bus.subscribe(UnitMoved, handler)
        for i in range(5):
            event: UnitMoved = {
                "unit_id": f"u{i}",
                "from_tile": (0, 0),
                "to_tile": (i, i),
            }
            bus.enqueue(event)
        assert bus.process_queue() == 5


class TestHandlerErrorIsolation:
    def test_one_handler_error_does_not_block_others(self):
        bus = EventBus()
        results: list[str] = []

        def bad_handler(e: UnitMoved):
            raise RuntimeError("boom")

        def good_handler(e: UnitMoved):
            results.append("ok")

        bus.subscribe(UnitMoved, bad_handler)
        bus.subscribe(UnitMoved, good_handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert results == ["ok"]

    def test_error_count_increments(self):
        bus = EventBus()

        def bad_handler(e: UnitMoved):
            raise ValueError("err")

        bus.subscribe(UnitMoved, bad_handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert bus._error_count == 1


class TestErrorRateStats:
    def test_error_rate_calculation(self):
        bus = EventBus()

        def bad_handler(e: UnitMoved):
            raise RuntimeError("x")

        bus.subscribe(UnitMoved, bad_handler)
        for _ in range(10):
            event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
            bus.publish(event)
        # Circuit breaker unsubscribes after 3 consecutive errors,
        # so only 3 out of 10 publishes result in errors.
        assert bus.error_rate == 0.3

    def test_no_errors_zero_rate(self):
        bus = EventBus()

        def ok_handler(e: UnitMoved):
            pass

        bus.subscribe(UnitMoved, ok_handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert bus.error_rate == 0.0


class TestEmptyEventNoHandlers:
    def test_publish_no_handlers_no_error(self):
        bus = EventBus()
        event: MoraleChanged = {
            "unit_id": "u1",
            "old_value": 80,
            "new_value": 60,
            "event_type": "test",
            "state_changed": False,
        }
        bus.publish(event)
        assert bus._total_published == 1


class TestDuplicateSubscribe:
    def test_duplicate_handler_called_multiple_times(self):
        bus = EventBus()
        received: list[UnitMoved] = []

        def handler(e: UnitMoved):
            received.append(e)

        bus.subscribe(UnitMoved, handler)
        bus.subscribe(UnitMoved, handler)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert len(received) == 2


class TestClearQueue:
    def test_clear_queue_empties(self):
        bus = EventBus()
        for i in range(3):
            event: UnitMoved = {
                "unit_id": f"u{i}",
                "from_tile": (0, 0),
                "to_tile": (i, i),
            }
            bus.enqueue(event)
        assert bus.queue_size == 3
        bus.clear_queue()
        assert bus.queue_size == 0


class TestResetStats:
    def test_reset_clears_counts(self):
        bus = EventBus()

        def bad(e: UnitMoved):
            raise RuntimeError("x")

        bus.subscribe(UnitMoved, bad)
        event: UnitMoved = {"unit_id": "u1", "from_tile": (0, 0), "to_tile": (1, 1)}
        bus.publish(event)
        assert bus._error_count > 0
        assert bus._total_published > 0
        bus.reset_stats()
        assert bus._error_count == 0
        assert bus._total_published == 0


class TestHandlerCount:
    def test_handler_count_property(self):
        bus = EventBus()

        def h1(e: UnitMoved):
            pass

        def h2(e: UnitMoved):
            pass

        def h3(e: MoraleChanged):
            pass

        bus.subscribe(UnitMoved, h1)
        bus.subscribe(UnitMoved, h2)
        bus.subscribe(MoraleChanged, h3)
        assert bus.handler_count == 3
