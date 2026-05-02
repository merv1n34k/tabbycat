"""Fight Club break table builder."""

from django.utils.html import escape
from django.utils.translation import gettext as _

from participants.models import Speaker
from standings.speakers import SpeakerStandingsGenerator
from utils.tables import TabbycatTableBuilder


def build_fight_club_break_table(view, category, standings):
    """Build a speaker-based break table for Fight Club mode."""
    tournament = category.tournament
    last_prelim = tournament.prelim_rounds().order_by('-seq').first()

    # Get speakers on breaking teams only; use the prefetched team objects
    # from standings so the FC descriptor has speaker_set available and
    # renders speaker-based names (not raw DB names).
    breaking_teams = [tsi.team for tsi in standings
                      if isinstance(tsi.break_rank, int)]
    team_by_pk = {t.pk: t for t in breaking_teams}

    speakers = Speaker.objects.filter(
        team__in=breaking_teams,
    ).select_related('team', 'team__institution')

    generator = SpeakerStandingsGenerator(('weighted_total',), ('rank',))
    speaker_standings = generator.generate(speakers, round=last_prelim)
    speaker_list = list(speaker_standings)

    # Map each speaker's team to the prefetched version so FC names render
    teams_for_table = [team_by_pk.get(info.speaker.team_id, info.speaker.team)
                       for info in speaker_list]

    table = TabbycatTableBuilder(view=view, title=escape(category.name), sort_key='Rk')
    table.add_ranking_columns(speaker_standings)
    table.add_speaker_columns([info.speaker for info in speaker_list])
    table.add_team_columns(teams_for_table)
    table.add_metric_columns(speaker_standings)
    return table
