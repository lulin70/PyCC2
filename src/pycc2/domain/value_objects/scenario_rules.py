"""Scenario special rules parsed from map JSON (CC2 parity P1-5)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioRules:
    """Immutable set of normalized scenario rule names."""

    rules: frozenset[str] = frozenset()

    @classmethod
    def from_map_data(cls, map_data: dict) -> ScenarioRules:
        """Parse ``special_rules`` into a normalized rule set."""
        raw = map_data.get("special_rules", []) if isinstance(map_data, dict) else []
        if isinstance(raw, str):
            raw = [raw]
        if isinstance(raw, dict):
            raw = [key for key, value in raw.items() if value]
        normalized = {
            str(rule).strip().lower() for rule in raw if isinstance(rule, str) and rule.strip()
        }
        return cls(rules=frozenset(normalized))

    def has(self, rule: str) -> bool:
        """Return True if the scenario enables *rule*."""
        return str(rule).strip().lower() in self.rules
