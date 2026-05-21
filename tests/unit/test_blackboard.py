from __future__ import annotations

import pytest

from pycc2.domain.ai.blackboard import Blackboard


@pytest.fixture
def bb() -> Blackboard:
    return Blackboard()


class TestBlackboardBasic:
    def test_set_and_get(self, bb: Blackboard):
        bb.set("key1", "value1")
        assert bb.get("key1") == "value1"

    def test_get_default_value(self, bb: Blackboard):
        assert bb.get("nonexistent") is None
        assert bb.get("nonexistent", 42) == 42

    def test_has_and_remove(self, bb: Blackboard):
        bb.set("key1", "value1")
        assert bb.has("key1") is True
        assert bb.remove("key1") is True
        assert bb.has("key1") is False
        assert bb.remove("key1") is False

    def test_clear(self, bb: Blackboard):
        bb.set("a", 1)
        bb.set("b", 2)
        bb.set("c", 3)
        bb.clear()
        assert bb.keys == []
        assert bb.get("a") is None


class TestBlackboardKeys:
    def test_keys_property(self, bb: Blackboard):
        bb.set("x", 1)
        bb.set("y", 2)
        bb.set("z", 3)
        keys = bb.keys
        assert set(keys) == {"x", "y", "z"}


class TestBlackboardSnapshot:
    def test_copy_snapshot_independence(self, bb: Blackboard):
        bb.set("data", [1, 2, 3])
        snapshot = bb.copy_snapshot()
        snapshot["data"].append(4)
        assert bb.get("data") == [1, 2, 3]
        assert snapshot["data"] == [1, 2, 3, 4]


class TestBlackboardTypeSafety:
    def test_any_type_storage(self, bb: Blackboard):
        bb.set("int_val", 42)
        bb.set("str_val", "hello")
        bb.set("list_val", [1, 2, 3])
        bb.set("dict_val", {"a": 1})
        bb.set("none_val", None)

        assert bb.get("int_val") == 42
        assert bb.get("str_val") == "hello"
        assert bb.get("list_val") == [1, 2, 3]
        assert bb.get("dict_val") == {"a": 1}
        assert bb.get("none_val") is None
