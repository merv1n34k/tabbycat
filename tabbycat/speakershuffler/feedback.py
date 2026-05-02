"""Fight Club feedback helpers: team table and historical team names."""

from django.utils.translation import gettext as _

from tournaments.models import Round

from .models import ShuffleLog


def build_fight_club_team_table(table, tournament, get_link_fn):
    """Build team rows: one row per team per released round, showing
    that round's team name. Only includes released rounds.

    ``get_link_fn(team_pk, round_id)`` must return a URL string.
    """

    # Only released rounds
    released_rounds = tournament.round_set.filter(
        draw_status=Round.Status.RELEASED,
        stage=Round.Stage.PRELIMINARY,
        silent=False,
    ).order_by('seq')

    rows = []
    for log in ShuffleLog.objects.filter(
        round__in=released_rounds,
    ).select_related('round').order_by('round__seq'):
        display_names = log.get_team_display_names()
        for team_pk, name in display_names.items():
            rows.append({
                'round_abbr': log.round.abbreviation,
                'round_id': log.round_id,
                'name': name,
                'team_pk': team_pk,
            })

    team_data = []
    round_data = []
    for row in rows:
        team_data.append({
            'text': row['name'],
            'link': get_link_fn(row['team_pk'], row['round_id']),
        })
        round_data.append(row['round_abbr'])

    table.add_column({'key': 'team', 'title': _("Team")}, team_data)
    table.add_column({'key': 'round', 'title': _("Round")}, round_data)


def get_historical_team_names(tournament, team_pk):
    """Return a dict mapping round_id -> historical team name for the given
    team in Fight Club mode."""
    historical = {}
    for log in ShuffleLog.objects.filter(round__tournament=tournament):
        display_names = log.get_team_display_names()
        if team_pk in display_names:
            historical[log.round_id] = display_names[team_pk]
    return historical


def patch_feedback_source_names(feedbacks, tournament):
    """Patch source team names on feedback objects with historical names from
    ShuffleLog so each feedback shows the speakers who were actually on that
    team in that round (not the current post-break assignment)."""
    logs = ShuffleLog.objects.filter(round__tournament=tournament)
    name_map = {}
    for log in logs:
        for team_pk, name in log.get_team_display_names().items():
            name_map[(log.round_id, team_pk)] = name

    for feedback in feedbacks:
        if not feedback.source_team or not feedback.source_team.team:
            continue
        round_id = feedback.source_team.debate.round_id
        historical = name_map.get((round_id, feedback.source_team.team_id))
        if historical:
            team = feedback.source_team.team
            team.__dict__['_fc_mode'] = False
            team.__dict__['short_name'] = historical
            team.__dict__['long_name'] = historical
