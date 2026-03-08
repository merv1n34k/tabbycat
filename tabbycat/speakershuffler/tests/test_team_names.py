"""Tests for the team name generator."""

from unittest import TestCase

from speakershuffler.team_names import CHARACTERS, generate_team_names


class GenerateTeamNamesTest(TestCase):

    def test_generates_correct_count(self):
        names = generate_team_names(10)
        self.assertEqual(len(names), 10)

    def test_names_contain_ampersand(self):
        names = generate_team_names(5)
        for name in names:
            self.assertIn(' & ', name)

    def test_no_duplicates(self):
        names = generate_team_names(20)
        self.assertEqual(len(names), len(set(names)))

    def test_respects_used_names(self):
        used = set()
        names1 = generate_team_names(5, used_names=used)
        names2 = generate_team_names(5, used_names=used)
        # No overlap between batches
        self.assertEqual(len(set(names1) & set(names2)), 0)

    def test_large_request(self):
        """Should handle request for many teams via fallback."""
        # More teams than character pairs available
        names = generate_team_names(200)
        self.assertEqual(len(names), 200)

    def test_characters_list_has_enough_entries(self):
        """Ensure we have enough characters for typical tournaments."""
        # A typical tournament has ~50 teams max, needs 100 characters
        self.assertGreaterEqual(len(CHARACTERS), 100)
