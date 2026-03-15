"""Core speaker shuffle algorithm for Fight Club mode.

Reshuffles speakers into new teams each round based on individual standings,
minimizing re-pairing of previous teammates and respecting personal conflicts.
"""

import logging
from collections import defaultdict

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.utils.translation import gettext as _

from availability.models import RoundAvailability
from draw.generator import DrawUserError
from participants.models import Speaker, Team
from standings.speakers import SpeakerStandingsGenerator

from .models import ShuffleLog, SpeakerConflict, SpeakerPairHistory
from .pairing import minimum_cost_matching

logger = logging.getLogger(__name__)

# Very high cost to make personal conflicts effectively hard constraints
CONFLICT_PENALTY = 1_000_000.0


def _get_available_teams(round):
    """Return teams that are marked available for this round.

    For elimination rounds, uses the breaking teams from the round's break
    category instead of RoundAvailability (which isn't populated for elim rounds).
    """
    if round.is_break_round and round.break_category is not None:
        return list(
            Team.objects.filter(
                breakingteam__break_category=round.break_category,
                breakingteam__break_rank__isnull=False,
            ).order_by('pk')
        )

    ct = ContentType.objects.get_for_model(Team)
    available_ids = RoundAvailability.objects.filter(
        content_type=ct, round=round,
    ).values_list('object_id', flat=True)
    return list(
        Team.objects.filter(
            pk__in=available_ids,
            tournament=round.tournament,
        ).order_by('pk')
    )


def _get_speakers_for_teams(teams):
    """Return speakers belonging to the given teams, ordered by team."""
    team_ids = [t.pk for t in teams]
    return list(
        Speaker.objects.filter(team_id__in=team_ids).select_related('team').order_by('pk')
    )


def _load_pair_history(tournament):
    """Load all pair history for the tournament.

    Returns: dict of {frozenset(s1_pk, s2_pk): count}
    """
    history = defaultdict(int)
    for s1_id, s2_id in SpeakerPairHistory.objects.filter(
        tournament=tournament,
    ).values_list('speaker1_id', 'speaker2_id'):
        history[frozenset((s1_id, s2_id))] += 1
    return history


def _load_personal_conflicts(tournament):
    """Load personal speaker conflicts.

    Returns: set of frozenset(s1_pk, s2_pk)
    """
    conflicts = set()
    for s1_id, s2_id in SpeakerConflict.objects.filter(
        tournament=tournament,
    ).values_list('speaker1_id', 'speaker2_id'):
        conflicts.add(frozenset((s1_id, s2_id)))
    return conflicts


def _populate_round1_history(tournament):
    """Auto-populate pair history and ShuffleLog from initial team assignments
    for round 1.  Called when first shuffle runs (round 2)."""
    round1 = tournament.round_set.filter(seq=1).first()
    if not round1:
        return

    teams = Team.objects.filter(tournament=tournament)

    # Pair history
    if not SpeakerPairHistory.objects.filter(round=round1).exists():
        rows = []
        for team in teams:
            speakers = list(Speaker.objects.filter(team=team).order_by('pk'))
            if len(speakers) == 2:
                s1, s2 = speakers
                if s1.pk > s2.pk:
                    s1, s2 = s2, s1
                rows.append(SpeakerPairHistory(
                    tournament=tournament,
                    speaker1=s1,
                    speaker2=s2,
                    round=round1,
                ))
        SpeakerPairHistory.objects.bulk_create(rows, ignore_conflicts=True)
        logger.info("Populated round 1 pair history: %d pairs", len(rows))

    # ShuffleLog for round 1 so historical draw display works
    if not ShuffleLog.objects.filter(round=round1).exists():
        assignments = {}
        team_names = {}
        for team in teams:
            team_names[str(team.pk)] = team.short_name
            for s in Speaker.objects.filter(team=team):
                assignments[str(s.pk)] = team.pk
        ShuffleLog.objects.create(
            round=round1,
            speaker_assignments=assignments,
            team_names=team_names,
        )


def _rank_speakers(tournament, round, speakers):
    """Rank speakers using the tournament's speaker standings precedence.
    Returns speakers sorted by rank (best first)."""
    metrics = tournament.pref('speaker_standings_precedence')
    generator = SpeakerStandingsGenerator(metrics, ('rank',))

    queryset = Speaker.objects.filter(pk__in=[s.pk for s in speakers])
    standings = generator.generate(queryset, round=round.prev)

    ranked = []
    for info in standings:
        ranked.append(info.speaker)

    # Add speakers not in standings (e.g., no scores yet) at the end
    ranked_pks = {s.pk for s in ranked}
    for s in speakers:
        if s.pk not in ranked_pks:
            ranked.append(s)

    return ranked


def perform_speaker_shuffle(round):
    """Main entry point: shuffle speakers into new teams for this round.

    Must be called before DrawManager.create().

    Steps:
    1. Rank speakers by individual standings up to the previous round
    2. Load pair history and personal conflicts
    3. Group into chunks of 8 (one BP room) and find optimal pairing
    4. Assign speakers to Team objects
    5. Rename teams with character-pair names
    6. Record pair history
    7. Create audit log

    Raises DrawUserError if speaker count doesn't match team slots.
    """
    tournament = round.tournament
    teams_in_debate = tournament.pref('teams_in_debate')
    substantive_speakers = tournament.pref('substantive_speakers')

    available_teams = _get_available_teams(round)
    speakers = _get_speakers_for_teams(available_teams)

    num_teams = len(available_teams)
    num_speakers = len(speakers)
    speakers_per_team = substantive_speakers

    if num_speakers != num_teams * speakers_per_team:
        raise DrawUserError(_(
            "Cannot shuffle: %(num_speakers)d speakers available but "
            "%(num_teams)d teams × %(spt)d speakers/team = %(expected)d expected."
        ) % {
            'num_speakers': num_speakers,
            'num_teams': num_teams,
            'spt': speakers_per_team,
            'expected': num_teams * speakers_per_team,
        })

    # Auto-populate round 1 history on first shuffle
    if round.seq == 2:
        _populate_round1_history(tournament)

    # Clear any existing history/log for this round (re-shuffle case)
    SpeakerPairHistory.objects.filter(round=round).delete()
    ShuffleLog.objects.filter(round=round).delete()

    # Rank speakers
    ranked_speakers = _rank_speakers(tournament, round, speakers)
    logger.info("Ranked %d speakers for shuffle", len(ranked_speakers))

    # Load pair history and conflicts
    pair_history = _load_pair_history(tournament)
    personal_conflicts = _load_personal_conflicts(tournament)
    penalty_weight = tournament.pref('speaker_repair_penalty')

    def pair_cost(s1, s2):
        key = frozenset([s1.pk, s2.pk])
        cost = pair_history[key] * penalty_weight
        if key in personal_conflicts:
            cost += CONFLICT_PENALTY
        return cost

    # Group speakers into chunks (one BP room = teams_in_debate × speakers_per_team)
    chunk_size = teams_in_debate * speakers_per_team
    assignments = {}  # speaker_pk -> team

    for i in range(0, len(ranked_speakers), chunk_size):
        chunk = ranked_speakers[i:i + chunk_size]
        if len(chunk) < chunk_size:
            raise DrawUserError(_("Incomplete room group during shuffle."))

        pairs = minimum_cost_matching(chunk, pair_cost)

        chunk_teams = available_teams[i // speakers_per_team:(i // speakers_per_team) + teams_in_debate]
        for pair_idx, (s1, s2) in enumerate(pairs):
            team = chunk_teams[pair_idx]
            assignments[s1.pk] = team
            assignments[s2.pk] = team

    # Apply assignments in a transaction
    with transaction.atomic():
        # Update Speaker.team FK
        for speaker_pk, team in assignments.items():
            Speaker.objects.filter(pk=speaker_pk).update(team=team)

        # Record pair history
        history_rows = []
        for pk1, pk2 in _extract_pairs(assignments):
            if pk1 > pk2:
                pk1, pk2 = pk2, pk1
            history_rows.append(SpeakerPairHistory(
                tournament=tournament,
                speaker1_id=pk1,
                speaker2_id=pk2,
                round=round,
            ))
        SpeakerPairHistory.objects.bulk_create(history_rows)

        # Create audit log with team names
        log_data = {str(spk_pk): team.pk for spk_pk, team in assignments.items()}
        team_names = {str(t.pk): t.short_name for t in available_teams}
        ShuffleLog.objects.create(
            round=round,
            speaker_assignments=log_data,
            team_names=team_names,
        )

    logger.info("Shuffle complete for %s: %d speakers across %d teams",
                round, len(assignments), num_teams)


def _extract_pairs(assignments):
    """Given {speaker_pk: team} mapping, yield (pk1, pk2) pairs per team."""
    team_speakers = defaultdict(list)
    for spk_pk, team in assignments.items():
        team_speakers[team.pk].append(spk_pk)

    for spk_pks in team_speakers.values():
        if len(spk_pks) == 2:
            yield tuple(spk_pks)


def get_current_shuffle_data(round):
    """Get the current speaker-team assignments for display in the edit UI.
    Returns a list of dicts: [{team: Team, speakers: [Speaker, ...]}]."""
    teams = _get_available_teams(round)
    result = []
    for team in teams:
        speakers = list(Speaker.objects.filter(team=team).order_by('pk'))
        result.append({'team': team, 'speakers': speakers})
    return result
