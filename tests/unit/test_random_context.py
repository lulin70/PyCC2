from __future__ import annotations

from pycc2.services.random_context import RandomContext


class TestFromSeed:
    def test_same_seed_produces_same_sequence(self):
        rc1 = RandomContext.from_seed(12345)
        rc2 = RandomContext.from_seed(12345)
        for _ in range(20):
            assert rc1.uniform() == rc2.uniform()

    def test_different_seeds_differ(self):
        rc1 = RandomContext.from_seed(1)
        rc2 = RandomContext.from_seed(2)
        results1 = [rc1.uniform() for _ in range(5)]
        results2 = [rc2.uniform() for _ in range(5)]
        assert results1 != results2

    def test_seed_property_returns_value(self):
        rc = RandomContext.from_seed(999)
        assert rc.seed == 999


class TestFromDeterministic:
    def test_fixed_seed_42(self):
        rc = RandomContext.from_deterministic()
        assert rc.seed == 42

    def test_deterministic_is_reproducible(self):
        r1 = RandomContext.from_deterministic()
        r2 = RandomContext.from_deterministic()
        assert r1.uniform() == r2.uniform()


class TestLive:
    def test_live_has_no_seed(self):
        rc = RandomContext.live()
        assert rc.seed is None

    def test_live_instances_differ(self):
        rc1 = RandomContext.live()
        rc2 = RandomContext.live()
        v1 = rc1.uniform()
        v2 = rc2.uniform()
        assert v1 != v2


class TestUniform:
    def test_default_range(self):
        rc = RandomContext.from_seed(0)
        for _ in range(100):
            v = rc.uniform()
            assert 0.0 <= v < 1.0

    def test_custom_range(self):
        rc = RandomContext.from_seed(0)
        for _ in range(100):
            v = rc.uniform(10.0, 20.0)
            assert 10.0 <= v <= 20.0


class TestGaussAndGaussian:
    def test_gauss_returns_float(self):
        rc = RandomContext.from_seed(0)
        v = rc.gauss(0, 1)
        assert isinstance(v, float)

    def test_gaussian_alias_same_as_gauss(self):
        rc1 = RandomContext.from_seed(42)
        rc2 = RandomContext.from_seed(42)
        assert rc1.gaussian(5, 2) == rc2.gauss(5, 2)


class TestRandint:
    def test_range_inclusive(self):
        rc = RandomContext.from_seed(0)
        for _ in range(200):
            v = rc.randint(1, 6)
            assert 1 <= v <= 6


class TestChoice:
    def test_choice_from_list(self):
        rc = RandomContext.from_seed(0)
        items = ["a", "b", "c", "d"]
        chosen = [rc.choice(items) for _ in range(20)]
        assert all(c in items for c in chosen)


class TestProbability:
    def test_probability_zero_always_false(self):
        rc = RandomContext.from_seed(0)
        for _ in range(100):
            assert rc.probability(0.0) is False

    def test_probability_one_always_true(self):
        rc = RandomContext.from_seed(0)
        for _ in range(100):
            assert rc.probability(1.0) is True

    def test_probability_half_approx(self):
        rc = RandomContext.from_seed(0)
        n = 10000
        trues = sum(1 for _ in range(n) if rc.probability(0.5))
        ratio = trues / n
        assert 0.45 < ratio < 0.55


class TestShuffle:
    def test_shuffle_modifies_in_place(self):
        rc = RandomContext.from_seed(0)
        original = list(range(10))
        seq = list(original)
        rc.shuffle(seq)
        assert seq == original or seq != original

    def test_shuffle_preserves_elements(self):
        rc = RandomContext.from_seed(0)
        seq = list(range(20))
        rc.shuffle(seq)
        assert sorted(seq) == list(range(20))


class TestReseed:
    def test_reseed_resets_sequence(self):
        rc = RandomContext.from_seed(99)
        first = [rc.uniform() for _ in range(5)]
        rc.reseed(99)
        second = [rc.uniform() for _ in range(5)]
        assert first == second
