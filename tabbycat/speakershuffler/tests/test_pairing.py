"""Tests for the minimum-weight perfect matching algorithm."""

from unittest import TestCase

from speakershuffler.pairing import _enumerate_perfect_matchings, minimum_cost_matching


class EnumerateMatchingsTest(TestCase):
    """Test that perfect matching enumeration produces correct results."""

    def test_empty_list(self):
        matchings = list(_enumerate_perfect_matchings([]))
        self.assertEqual(matchings, [()])

    def test_two_items(self):
        matchings = list(_enumerate_perfect_matchings([1, 2]))
        self.assertEqual(matchings, [((1, 2),)])

    def test_four_items(self):
        """4 items should produce exactly 3 perfect matchings."""
        matchings = list(_enumerate_perfect_matchings([1, 2, 3, 4]))
        self.assertEqual(len(matchings), 3)
        # Verify all matchings are valid partitions
        for matching in matchings:
            all_items = set()
            for a, b in matching:
                all_items.add(a)
                all_items.add(b)
            self.assertEqual(all_items, {1, 2, 3, 4})

    def test_six_items(self):
        """6 items should produce exactly 15 perfect matchings."""
        matchings = list(_enumerate_perfect_matchings([1, 2, 3, 4, 5, 6]))
        self.assertEqual(len(matchings), 15)

    def test_eight_items(self):
        """8 items should produce exactly 105 perfect matchings."""
        matchings = list(_enumerate_perfect_matchings(list(range(8))))
        self.assertEqual(len(matchings), 105)

    def test_all_matchings_are_valid_partitions(self):
        """Every matching should cover all items exactly once."""
        items = list(range(8))
        for matching in _enumerate_perfect_matchings(items):
            covered = set()
            for a, b in matching:
                self.assertNotIn(a, covered)
                self.assertNotIn(b, covered)
                covered.add(a)
                covered.add(b)
            self.assertEqual(covered, set(items))


class MinimumCostMatchingTest(TestCase):
    """Test that minimum_cost_matching finds the optimal solution."""

    def test_zero_cost(self):
        """When all pairs have zero cost, any matching is optimal."""
        speakers = [1, 2, 3, 4]
        result = minimum_cost_matching(speakers, lambda a, b: 0)
        self.assertEqual(len(result), 2)
        all_speakers = set()
        for a, b in result:
            all_speakers.add(a)
            all_speakers.add(b)
        self.assertEqual(all_speakers, {1, 2, 3, 4})

    def test_prefers_low_cost_pairs(self):
        """Should pair items with lowest cost together."""
        speakers = [1, 2, 3, 4]

        def cost(a, b):
            # Make (1,2) and (3,4) very cheap, others expensive
            if {a, b} == {1, 2} or {a, b} == {3, 4}:
                return 0
            return 100

        result = minimum_cost_matching(speakers, cost)
        result_sets = [frozenset(pair) for pair in result]
        self.assertIn(frozenset({1, 2}), result_sets)
        self.assertIn(frozenset({3, 4}), result_sets)

    def test_conflict_avoidance(self):
        """Should avoid high-cost (conflicting) pairs."""
        speakers = list(range(8))

        def cost(a, b):
            # Make (0,1) a conflict
            if {a, b} == {0, 1}:
                return 1_000_000
            return 0

        result = minimum_cost_matching(speakers, cost)
        result_sets = [frozenset(pair) for pair in result]
        self.assertNotIn(frozenset({0, 1}), result_sets)

    def test_balances_costs(self):
        """Should minimize total cost, not just individual pair costs."""
        speakers = [1, 2, 3, 4]

        def cost(a, b):
            costs = {
                frozenset({1, 2}): 10,
                frozenset({1, 3}): 5,
                frozenset({1, 4}): 5,
                frozenset({2, 3}): 5,
                frozenset({2, 4}): 5,
                frozenset({3, 4}): 10,
            }
            return costs[frozenset({a, b})]

        result = minimum_cost_matching(speakers, cost)
        total = sum(cost(a, b) for a, b in result)
        # Optimal is 10 (e.g., (1,2)+(3,4) or any combo summing to 10)
        self.assertEqual(total, 10)

    def test_eight_speakers(self):
        """Test with realistic 8-speaker scenario."""
        speakers = list(range(8))

        def cost(a, b):
            # Previously paired: 0-1, 2-3, 4-5, 6-7
            previous = [{0, 1}, {2, 3}, {4, 5}, {6, 7}]
            if {a, b} in previous:
                return 1000
            return 0

        result = minimum_cost_matching(speakers, cost)
        result_sets = [frozenset(pair) for pair in result]

        # None of the previous pairings should appear
        for prev in [{0, 1}, {2, 3}, {4, 5}, {6, 7}]:
            self.assertNotIn(frozenset(prev), result_sets)
