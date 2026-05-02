"""Break generation and standings helpers for Fight Club mode."""

import logging

from django.utils.translation import gettext_lazy as _

from breakqual.base import BreakGeneratorError, StandardBreakGenerator

logger = logging.getLogger(__name__)


class FightClubBreakGenerator(StandardBreakGenerator):
    """Break generator for Fight Club mode.

    Selects the top N individual speakers by speaker standings precedence,
    then reassigns them onto the first break_size teams (by PK) so that
    only breaking speakers end up on breaking team objects. Non-breaking
    speakers are moved to the remaining teams.
    """

    key = "fight-club"

    def retrieve_standings(self):
        from django.db import transaction

        from participants.models import Speaker
        from standings.speakers import SpeakerStandingsGenerator

        tournament = self.category.tournament
        speakers_per_team = tournament.pref('substantive_speakers')
        num_breaking_speakers = self.break_size * speakers_per_team

        # Get the last preliminary round
        last_prelim = tournament.prelim_rounds().order_by('-seq').first()
        if last_prelim is None:
            raise BreakGeneratorError(_("There are no preliminary rounds."))

        # Rank ALL speakers by placement-weighted total (PW Tot)
        all_speakers = Speaker.objects.filter(team__in=self.team_queryset)
        generator = SpeakerStandingsGenerator(('weighted_total',), ('rank',))
        speaker_standings = generator.generate(all_speakers, round=last_prelim)
        all_speaker_infos = list(speaker_standings)

        # Select top N breaking speakers
        breaking_speaker_infos = all_speaker_infos[:num_breaking_speakers]
        non_breaking_speaker_infos = all_speaker_infos[num_breaking_speakers:]

        # Sort teams by PK: first break_size = "break teams", rest = "other teams"
        all_teams = list(self.team_queryset.order_by('pk'))
        break_teams = all_teams[:self.break_size]
        other_teams = all_teams[self.break_size:]

        # Reassign speakers to team objects
        speaker_scores = {}
        for info in all_speaker_infos:
            speaker_scores[info.speaker.pk] = info.metrics.get('weighted_total', 0) or 0

        with transaction.atomic():
            for i, info in enumerate(breaking_speaker_infos):
                team_idx = i // speakers_per_team
                if team_idx < len(break_teams):
                    Speaker.objects.filter(pk=info.speaker.pk).update(team=break_teams[team_idx])

            for i, info in enumerate(non_breaking_speaker_infos):
                team_idx = i // speakers_per_team
                if team_idx < len(other_teams):
                    Speaker.objects.filter(pk=info.speaker.pk).update(team=other_teams[team_idx])

        # Build team standings for break teams only
        team_scores = {}
        for idx, team in enumerate(break_teams):
            start = idx * speakers_per_team
            end = start + speakers_per_team
            team_spk_infos = breaking_speaker_infos[start:end]
            team_scores[team] = sum(speaker_scores.get(info.speaker.pk, 0) for info in team_spk_infos)

        standings = build_fight_club_team_standings(break_teams, team_scores)
        self.standings = list(standings)


def build_fight_club_team_standings(teams, team_scores):
    """Build a Standings object for Fight Club teams, sorted by PW Tot.

    Args:
        teams: iterable of Team objects
        team_scores: {team: score} mapping (placement-weighted totals)
    """
    from standings.base import Standings
    from standings.ranking import BasicRankAnnotator

    standings = Standings(teams)
    standings.record_added_metric(
        'pw_total', _("placement-weighted total"), _("PW Tot"), None, False,
    )
    for team in teams:
        standings.add_metric(team, 'pw_total', team_scores[team])

    standings.sort(['pw_total'])
    BasicRankAnnotator(['pw_total']).run(standings)
    return standings


def generate_fight_club_standings(category, teams):
    """Generate standings for Fight Club mode, ranking teams by sum of
    their current speakers' placement-weighted scores."""
    from participants.models import Speaker
    from standings.speakers import SpeakerStandingsGenerator

    tournament = category.tournament
    last_prelim = tournament.prelim_rounds().order_by('-seq').first()

    speaker_qs = Speaker.objects.filter(team__in=teams)
    generator = SpeakerStandingsGenerator(('weighted_total',), ('rank',))
    speaker_standings = generator.generate(speaker_qs, round=last_prelim)

    speaker_scores = {}
    for info in speaker_standings:
        speaker_scores[info.speaker.pk] = info.metrics.get('weighted_total', 0) or 0

    team_scores = {}
    for team in teams:
        team_speaker_pks = Speaker.objects.filter(team=team).values_list('pk', flat=True)
        team_scores[team] = sum(speaker_scores.get(pk, 0) for pk in team_speaker_pks)

    return build_fight_club_team_standings(teams, team_scores)
