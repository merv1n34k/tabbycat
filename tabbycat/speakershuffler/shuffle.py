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
    For subsequent break rounds, narrows to only teams that won the previous round.
    """
    if round.is_break_round and round.break_category is not None:
        teams_qs = Team.objects.filter(
            breakingteam__break_category=round.break_category,
            breakingteam__break_rank__isnull=False,
        )
        # For subsequent break rounds, keep only teams that won the previous round
        if round.prev is not None and round.prev.is_break_round:
            from results.models import TeamScore
            winning_team_ids = TeamScore.objects.filter(
                ballot_submission__confirmed=True,
                debate_team__debate__round=round.prev,
                win=True,
            ).values_list('debate_team__team_id', flat=True)
            teams_qs = teams_qs.filter(pk__in=winning_team_ids)
        return list(teams_qs.order_by('pk'))

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


def _get_speakers_for_teams(teams, round=None):
    """Return speakers belonging to the given teams, ordered by team.

    For subsequent break rounds, returns only speakers who were on a
    winning side in the previous break round — regardless of their
    current team FK (which may be stale from an old shuffle).
    Uses ShuffleLog as the primary source, falling back to SpeakerScore.
    """
    # For subsequent break rounds, ignore current FK and select by advancement
    if round is not None and round.is_break_round and round.prev is not None and round.prev.is_break_round:
        from results.models import TeamScore
        winning_team_ids = set(TeamScore.objects.filter(
            ballot_submission__confirmed=True,
            debate_team__debate__round=round.prev,
            win=True,
        ).values_list('debate_team__team_id', flat=True))

        advancing_speaker_ids = None
        if winning_team_ids:
            prev_log = ShuffleLog.objects.filter(round=round.prev).order_by('-timestamp').first()
            if prev_log and prev_log.speaker_assignments:
                advancing_speaker_ids = [
                    int(spk_pk) for spk_pk, team_pk in prev_log.speaker_assignments.items()
                    if team_pk in winning_team_ids
                ]
            else:
                from results.models import SpeakerScore
                winning_dt_ids = TeamScore.objects.filter(
                    ballot_submission__confirmed=True,
                    debate_team__debate__round=round.prev,
                    win=True,
                ).values_list('debate_team_id', flat=True)
                advancing_speaker_ids = list(SpeakerScore.objects.filter(
                    ballot_submission__confirmed=True,
                    debate_team__in=winning_dt_ids,
                ).values_list('speaker_id', flat=True))

        if advancing_speaker_ids:
            return list(Speaker.objects.filter(pk__in=advancing_speaker_ids)
                        .select_related('team').order_by('pk'))

    # Default: speakers currently FK'd to the given teams
    team_ids = [t.pk for t in teams]
    return list(Speaker.objects.filter(team_id__in=team_ids)
                .select_related('team').order_by('pk'))


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

    # ShuffleLog for round 1 so historical draw display works.
    # Only include speakers who actually scored in R1 (not the full roster).
    if not ShuffleLog.objects.filter(round=round1).exists():
        from results.models import SpeakerScore
        scored = set(SpeakerScore.objects.filter(
            ballot_submission__confirmed=True,
            debate_team__debate__round=round1,
        ).values_list('speaker_id', flat=True))

        assignments = {}
        for team in teams:
            for s in Speaker.objects.filter(team=team):
                if scored and s.pk not in scored:
                    continue  # skip bench speakers
                assignments[str(s.pk)] = team.pk
        ShuffleLog.objects.create(
            round=round1,
            speaker_assignments=assignments,
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
    5. Record pair history
    6. Create audit log

    Raises DrawUserError if speaker count doesn't match team slots.
    """
    tournament = round.tournament
    teams_in_debate = tournament.pref('teams_in_debate')
    substantive_speakers = tournament.pref('substantive_speakers')

    available_teams = _get_available_teams(round)
    speakers = _get_speakers_for_teams(available_teams, round=round)

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

    # Load personal conflicts (hard constraints)
    personal_conflicts = _load_personal_conflicts(tournament)

    def pair_cost(s1, s2):
        key = frozenset([s1.pk, s2.pk])
        cost = 0.0
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

        # Create audit log
        log_data = {str(spk_pk): team.pk for spk_pk, team in assignments.items()}
        ShuffleLog.objects.create(
            round=round,
            speaker_assignments=log_data,
        )

    # For break rounds, move non-advancing speakers off the available teams
    # so they don't pollute team names and speaker counts.
    if round.is_break_round:
        assigned_pks = set(assignments.keys())
        available_team_ids = [t.pk for t in available_teams]
        stale_speakers = Speaker.objects.filter(
            team_id__in=available_team_ids,
        ).exclude(pk__in=assigned_pks)
        if stale_speakers.exists():
            # Find non-available break teams to park them on
            all_break_team_ids = set(Team.objects.filter(
                breakingteam__break_category=round.break_category,
                breakingteam__break_rank__isnull=False,
            ).values_list('pk', flat=True))
            other_team_ids = all_break_team_ids - set(available_team_ids)
            if other_team_ids:
                park_team_id = min(other_team_ids)
                count = stale_speakers.update(team_id=park_team_id)
                logger.info("Moved %d non-advancing speakers off available teams", count)

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
    advancing_speakers = _get_speakers_for_teams(teams, round=round)

    # Determine speaker→team mapping.  Priority:
    # 1. This round's ShuffleLog (shuffle already ran for this round)
    # 2. Previous round's ShuffleLog (no shuffle yet, show pre-shuffle state)
    # 3. Current FK (fallback)
    speaker_team_map = None
    if round.is_break_round and round.prev is not None and round.prev.is_break_round:
        current_log = ShuffleLog.objects.filter(round=round).order_by('-timestamp').first()
        if current_log and current_log.speaker_assignments:
            speaker_team_map = {
                int(spk_pk): team_pk
                for spk_pk, team_pk in current_log.speaker_assignments.items()
            }
        else:
            prev_log = ShuffleLog.objects.filter(round=round.prev).order_by('-timestamp').first()
            if prev_log and prev_log.speaker_assignments:
                speaker_team_map = {
                    int(spk_pk): team_pk
                    for spk_pk, team_pk in prev_log.speaker_assignments.items()
                }

    result = []
    for team in teams:
        if speaker_team_map:
            speakers = [s for s in advancing_speakers if speaker_team_map.get(s.pk) == team.pk]
        else:
            speakers = [s for s in advancing_speakers if s.team_id == team.pk]
        result.append({'team': team, 'speakers': speakers})
    return result
