"""Speaker standings metric annotator for Fight Club mode."""

from django.db.models import Q
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from results.models import SpeakerScore, TeamScore
from standings.metrics import BaseMetricAnnotator
from standings.templatetags.standingsformat import metricformat
from tournaments.models import Round


class PlacementWeightedScoreMetricAnnotator(BaseMetricAnnotator):
    """Metric annotator for placement-weighted total speaker score.

    Multiplies each speech score by a coefficient based on the team's placement
    in that debate (1st=1.1, 2nd=1.075, 3rd=1.05, 4th=1.0), then sums.
    """
    key = "weighted_total"
    name = _("placement-weighted total")
    abbr = _("PW Tot")

    COEFFICIENTS = {3: 1.1, 2: 1.075, 1: 1.05, 0: 1.0}

    def annotate(self, queryset, standings, round=None):
        speakers = list(standings.infos.keys())
        speaker_ids = [s.pk for s in speakers]
        if not speaker_ids:
            return

        # Batch query SpeakerScore rows
        ss_filter = Q(
            ballot_submission__confirmed=True,
            debate_team__debate__round__stage=Round.Stage.PRELIMINARY,
            ghost=False,
            position__lte=round.tournament.last_substantive_position,
            speaker_id__in=speaker_ids,
        )
        if round is not None:
            ss_filter &= Q(debate_team__debate__round__seq__lte=round.seq)

        scores = list(SpeakerScore.objects.filter(ss_filter).values_list(
            'speaker_id', 'score', 'debate_team_id', 'ballot_submission_id',
        ))

        # Batch query TeamScore rows for placement points
        dt_bs_pairs = {(dt_id, bs_id) for _, _, dt_id, bs_id in scores}
        ts_lookup = {}
        if dt_bs_pairs:
            ts_rows = TeamScore.objects.filter(
                ballot_submission__confirmed=True,
            ).values_list('debate_team_id', 'ballot_submission_id', 'points')
            for dt_id, bs_id, points in ts_rows:
                if (dt_id, bs_id) in dt_bs_pairs:
                    ts_lookup[(dt_id, bs_id)] = points

        # Compute weighted total per speaker
        weighted_totals = {}
        for speaker_id, score, dt_id, bs_id in scores:
            points = ts_lookup.get((dt_id, bs_id), 0)
            coeff = self.COEFFICIENTS.get(points, 1.0)
            weighted_totals[speaker_id] = weighted_totals.get(speaker_id, 0) + float(score) * coeff

        for speaker in speakers:
            standings.add_metric(speaker, self.key, weighted_totals.get(speaker.pk, 0))

    def per_round_pw_scores(self, speaker_ids, rounds, tournament):
        """Reuse annotate() query logic but return per-round PW scores
        as a dict mapping (speaker_id, round_index) -> pw_score."""
        if not speaker_ids:
            return {}

        round_lookup = {r.id: i for i, r in enumerate(rounds)}
        ss_filter = Q(
            ballot_submission__confirmed=True,
            debate_team__debate__round__in=rounds,
            ghost=False,
            position__lte=tournament.last_substantive_position,
            speaker_id__in=speaker_ids,
        )
        scores = list(SpeakerScore.objects.filter(ss_filter).values_list(
            'speaker_id', 'score', 'debate_team_id',
            'ballot_submission_id', 'debate_team__debate__round_id',
        ))

        dt_bs_pairs = {(dt_id, bs_id) for _, _, dt_id, bs_id, _ in scores}
        ts_lookup = {}
        if dt_bs_pairs:
            for dt_id, bs_id, points in TeamScore.objects.filter(
                ballot_submission__confirmed=True,
            ).values_list('debate_team_id', 'ballot_submission_id', 'points'):
                if (dt_id, bs_id) in dt_bs_pairs:
                    ts_lookup[(dt_id, bs_id)] = points

        pw_map = {}
        for speaker_id, score, dt_id, bs_id, round_id in scores:
            points = ts_lookup.get((dt_id, bs_id))
            coeff = self.COEFFICIENTS.get(points if points is not None else 0, 1.0)
            idx = round_lookup.get(round_id)
            if idx is not None:
                pw_map[(speaker_id, idx)] = float(score) * coeff
        return pw_map


def format_scores_with_pw(standings, rounds, tournament):
    """Return scores_data with per-round PW scores in brackets.

    Sorting is unaffected — this only changes the per-round cell display.
    """
    annotator = PlacementWeightedScoreMetricAnnotator()
    speaker_ids = [info.instance_id for info in standings]
    pw_map = annotator.per_round_pw_scores(speaker_ids, rounds, tournament)

    scores_data = []
    for standing in standings:
        row = []
        sid = standing.instance_id
        for i, raw in enumerate(standing.scores):
            if raw is None:
                row.append('—')
            else:
                pw = pw_map.get((sid, i))
                if pw is not None:
                    row.append(mark_safe(
                        f"{metricformat(raw)} <small class=\"text-muted\">({metricformat(pw)})</small>",
                    ))
                else:
                    row.append(metricformat(raw))
        scores_data.append(row)
    return scores_data
