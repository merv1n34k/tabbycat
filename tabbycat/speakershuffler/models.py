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

    class Meta:
        verbose_name = _("shuffle log")
        verbose_name_plural = _("shuffle logs")
        ordering = ['-timestamp']

    def __str__(self):
        return f"Shuffle for {self.round} at {self.timestamp}"
