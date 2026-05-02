"""Tests for the shuffle algorithm helper functions."""

from collections import defaultdict
from unittest import TestCase

from speakershuffler.shuffle import _extract_pairs


class ExtractPairsTest(TestCase):

    def test_basic_extraction(self):
        """Pairs are correctly extracted from assignments dict."""

        class FakeTeam:
            def __init__(self, pk):
                self.pk = pk

        t1 = FakeTeam(100)
        t2 = FakeTeam(200)
        assignments = {1: t1, 2: t1, 3: t2, 4: t2}

        pairs = list(_extract_pairs(assignments))
        self.assertEqual(len(pairs), 2)

        # Verify all speaker PKs are covered
        all_pks = set()
        for p in pairs:
            all_pks.update(p)
        self.assertEqual(all_pks, {1, 2, 3, 4})

    def test_single_team(self):
        class FakeTeam:
            def __init__(self, pk):
                self.pk = pk

        t1 = FakeTeam(100)
        assignments = {1: t1, 2: t1}
        pairs = list(_extract_pairs(assignments))
        self.assertEqual(len(pairs), 1)

    def test_empty_assignments(self):
        pairs = list(_extract_pairs({}))
        self.assertEqual(len(pairs), 0)
