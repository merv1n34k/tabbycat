from django.db import models
from django.utils.translation import gettext_lazy as _


class SpeakerPairHistory(models.Model):
    """Records that two speakers were teammates in a given round.
    Canonical ordering: speaker1.pk < speaker2.pk."""

    tournament = models.ForeignKey(
        'tournaments.Tournament', models.CASCADE,
        verbose_name=_("tournament"),
    )
    speaker1 = models.ForeignKey(
        'participants.Speaker', models.CASCADE,
        related_name='pair_history_as_first',
        verbose_name=_("speaker 1"),
    )
    speaker2 = models.ForeignKey(
        'participants.Speaker', models.CASCADE,
        related_name='pair_history_as_second',
        verbose_name=_("speaker 2"),
    )
    round = models.ForeignKey(
        'tournaments.Round', models.CASCADE,
        verbose_name=_("round"),
    )

    class Meta:
        verbose_name = _("speaker pair history")
        verbose_name_plural = _("speaker pair histories")
        constraints = [
            models.UniqueConstraint(
                fields=['speaker1', 'speaker2', 'round'],
                name='unique_speaker_pair_per_round',
            ),
        ]

    def save(self, *args, **kwargs):
        # Enforce canonical ordering: speaker1.pk < speaker2.pk
        if self.speaker1_id and self.speaker2_id and self.speaker1_id > self.speaker2_id:
            self.speaker1_id, self.speaker2_id = self.speaker2_id, self.speaker1_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.speaker1} & {self.speaker2} (Round {self.round.seq})"


class ShuffleLog(models.Model):
    """Audit trail for speaker shuffles."""

    round = models.ForeignKey(
        'tournaments.Round', models.CASCADE,
        verbose_name=_("round"),
    )
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name=_("timestamp"))
    speaker_assignments = models.JSONField(
        verbose_name=_("speaker assignments"),
        help_text=_("Mapping of speaker ID to team ID"),
    )
    team_names = models.JSONField(
        verbose_name=_("team names"),
        help_text=_("Mapping of team ID to team name for this round"),
        default=dict, blank=True,
    )

    class Meta:
        verbose_name = _("shuffle log")
        verbose_name_plural = _("shuffle logs")
        ordering = ['-timestamp']

    def get_team_display_names(self, speaker_names=None):
        """Derive team display names from speaker assignments.

        Args:
            speaker_names: optional {speaker_pk: name} dict to avoid DB queries.
        Returns:
            {team_pk (int): "Speaker1 & Speaker2"}
        """
        if speaker_names is None:
            from participants.models import Speaker
            spk_pks = [int(pk) for pk in self.speaker_assignments.keys()]
            speaker_names = dict(Speaker.objects.filter(pk__in=spk_pks).values_list('pk', 'name'))

        team_speakers = {}
        for spk_pk_str, team_pk in self.speaker_assignments.items():
            name = speaker_names.get(int(spk_pk_str), f"Speaker #{spk_pk_str}")
            team_speakers.setdefault(int(team_pk), []).append(name)

        return {team_pk: " & ".join(sorted(names)) for team_pk, names in team_speakers.items()}

    def __str__(self):
        return f"Shuffle for {self.round} at {self.timestamp}"


class SpeakerConflict(models.Model):
    """Personal conflict between two speakers — they should not be paired.
    Canonical ordering: speaker1.pk < speaker2.pk."""

    tournament = models.ForeignKey(
        'tournaments.Tournament', models.CASCADE,
        verbose_name=_("tournament"),
    )
    speaker1 = models.ForeignKey(
        'participants.Speaker', models.CASCADE,
        related_name='conflict_as_first',
        verbose_name=_("speaker 1"),
    )
    speaker2 = models.ForeignKey(
        'participants.Speaker', models.CASCADE,
        related_name='conflict_as_second',
        verbose_name=_("speaker 2"),
    )

    class Meta:
        verbose_name = _("speaker conflict")
        verbose_name_plural = _("speaker conflicts")
        constraints = [
            models.UniqueConstraint(
                fields=['speaker1', 'speaker2'],
                name='unique_speaker_conflict',
            ),
        ]

    def save(self, *args, **kwargs):
        if self.speaker1_id and self.speaker2_id and self.speaker1_id > self.speaker2_id:
            self.speaker1_id, self.speaker2_id = self.speaker2_id, self.speaker1_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.speaker1} conflicts with {self.speaker2}"
