"""Historical speaker patching for Fight Club mode."""


def patch_historical_speakers(debates):
    """Replace each team's prefetched speaker_set with the speakers who
    actually debated in this round (from SpeakerScore), so the
    FightClubDescriptor renders correct speaker names.

    Works for all rounds -- R1 (no shuffle), shuffled rounds, break
    rounds. For the current round before results are entered, the
    prefetch cache already has the correct speakers via FK, so
    patching is a no-op (no confirmed SpeakerScores exist yet)."""
    from participants.models import Speaker
    from results.models import SpeakerScore

    # Collect all DebateTeam IDs in one pass
    dt_map = {}  # {debate_team_id: team}
    for debate in debates:
        if not hasattr(debate, '_prefetched_objects_cache'):
            continue
        for dt in debate.debateteam_set.all():
            dt_map[dt.pk] = dt.team

    if not dt_map:
        return

    scored = SpeakerScore.objects.filter(
        debate_team_id__in=dt_map.keys(),
        ballot_submission__confirmed=True,
        ghost=False,
    ).select_related('speaker').order_by('speaker__name')

    team_speakers = {}  # {team_pk: [Speaker, ...]}
    seen = set()
    for ss in scored:
        team = dt_map[ss.debate_team_id]
        key = (team.pk, ss.speaker_id)
        if key not in seen:
            seen.add(key)
            team_speakers.setdefault(team.pk, []).append(ss.speaker)

    for team in dt_map.values():
        speakers = team_speakers.get(team.pk, [])
        # List for the FightClubDescriptor (reads prefetch cache directly)
        team._prefetched_objects_cache['speaker_set'] = speakers
        # QuerySet for forms that need .all() (e.g. ModelChoiceField)
        team.__dict__['speakers'] = Speaker.objects.filter(
            pk__in=[s.pk for s in speakers],
        )
