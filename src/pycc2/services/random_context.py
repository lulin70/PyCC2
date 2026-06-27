"""Random number generator context implementing IRandomNumberGenerator.

Wraps Python's random.Random with seed management for deterministic replays
and testability, exposing the domain RNG interface to game systems.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from pycc2.domain.interfaces import IRandomNumberGenerator


@dataclass(slots=True)
class RandomContext(IRandomNumberGenerator):
    """Seedable RNG adapter exposing the domain IRandomNumberGenerator interface."""

    _rng: random.Random = field(default_factory=random.Random)
    _seed: int | None = None

    @classmethod
    def from_seed(cls, seed: int) -> RandomContext:
        """创建确定性RNG(用于测试回放)"""
        instance = cls(_rng=random.Random(seed))
        instance._seed = seed
        return instance

    @classmethod
    def from_deterministic(cls) -> RandomContext:
        """创建固定seed=42的确定性实例"""
        return cls.from_seed(42)

    @classmethod
    def live(cls) -> RandomContext:
        """创建使用系统时间的真实随机实例"""
        return cls()

    @property
    def seed(self) -> int | None:
        return self._seed

    def uniform(self, low: float = 0.0, high: float = 1.0) -> float:
        return self._rng.uniform(low, high)

    def gauss(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        return self._rng.gauss(mu, sigma)

    def gaussian(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        """Alias for BallisticEngine兼容"""
        return self.gauss(mu, sigma)

    def randint(self, low: int, high: int) -> int:
        return self._rng.randint(low, high)

    def choice(self, seq: list) -> Any:
        return self._rng.choice(seq)

    def probability(self, p: float) -> bool:
        """返回True的概率为p (等价于 uniform() < p)"""
        return self._rng.random() < p

    def shuffle(self, seq: list) -> None:
        """原位打乱列表"""
        self._rng.shuffle(seq)

    def reseed(self, seed: int) -> None:
        """重新设置seed"""
        self._seed = seed
        self._rng.seed(seed)
