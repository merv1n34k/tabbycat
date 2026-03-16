"""Draw manager for Fight Club mode."""

import logging
from typing import List, Tuple, TYPE_CHECKING

from draw.manager import BaseDrawManager

if TYPE_CHECKING:
    from participants.models import Team

logger = logging.getLogger(__name__)


class FightClubDrawManager(BaseDrawManager):
    """Power-paired draw for Fight Club mode.

    Instead of using team standings (meaningless after a speaker shuffle),
    ranks teams by their current speakers' individual standings.  Teams from
    the same shuffle chunk receive the same bracket value so the Hungarian
    algorithm keeps them in one room.
    """

    generator_type = "power_paired"

    def get_relevant_options(self):
        options = super().get_relevant_options()
        if self.teams_in_debate == 4:
            options.extend(["pullup", "position_cost", "assignment_method", "renyi_order", "exponent"])
        return options

    def get_teams(self) -> Tuple[List['Team'], List['Team']]:
        from participants.models import Speaker
        from standings.speakers import SpeakerStandingsGenerator

        teams, byes = super().get_teams()
        tournament = self.round.tournament

        # Rank speakers by individual standings
        metrics = tournament.pref('speaker_standings_precedence')
        generator = SpeakerStandingsGenerator(metrics, ('rank',))
        speaker_qs = Speaker.objects.filter(team__in=teams)
        standings = generator.generate(speaker_qs, round=self.round.prev)

        # Build speaker rank lookup (lower = better)
        speaker_rank = {}
        for i, info in enumerate(standings):
            speaker_rank[info.speaker.pk] = i

        # For each team, compute average speaker rank
        team_scores = {}
        for team in teams:
            team_speakers = Speaker.objects.filter(team=team).values_list('pk', flat=True)
            ranks = [speaker_rank.get(pk, len(speaker_rank)) for pk in team_speakers]
            team_scores[team.pk] = sum(ranks) / max(len(ranks), 1)

        # Sort teams by average speaker rank (best first)
        teams.sort(key=lambda t: team_scores[t.pk])

        # Assign bracket points: groups of teams_in_debate get the same points
        n_rooms = len(teams) // self.teams_in_debate
        for i, team in enumerate(teams):
            bracket = n_rooms - (i // self.teams_in_debate)
            team.points = bracket
            team.subrank = (i % self.teams_in_debate) + 1

        return teams, byes
