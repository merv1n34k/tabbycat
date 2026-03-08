import json
import logging

from django.contrib import messages
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.translation import gettext as _
from django.views.generic.base import TemplateView, View

from participants.models import Speaker
from tournaments.mixins import RoundMixin
from utils.mixins import AdministratorMixin

from .models import ShuffleLog, SpeakerPairHistory
from .shuffle import get_current_shuffle_data, perform_speaker_shuffle

logger = logging.getLogger(__name__)


class EditSpeakerShuffleView(AdministratorMixin, RoundMixin, TemplateView):
    """Drag-and-drop UI for reviewing and manually adjusting shuffled teams."""
    template_name = 'edit_speaker_shuffle.html'
    page_title = 'Edit Speaker Shuffle'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        shuffle_data = get_current_shuffle_data(self.round)

        # Serialize for the template
        teams_data = []
        for entry in shuffle_data:
            team = entry['team']
            speakers = entry['speakers']
            teams_data.append({
                'id': team.pk,
                'name': team.short_name,
                'reference': team.reference,
                'speakers': [
                    {
                        'id': s.pk,
                        'name': s.name,
                    }
                    for s in speakers
                ],
            })

        context['shuffle_data_json'] = json.dumps(teams_data)
        context['has_shuffle_log'] = ShuffleLog.objects.filter(round=self.round).exists()

        # Load pair history for conflict display
        pair_history = {}
        for row in SpeakerPairHistory.objects.filter(
            tournament=self.tournament,
        ).values_list('speaker1_id', 'speaker2_id'):
            key = f"{min(row)}-{max(row)}"
            pair_history[key] = pair_history.get(key, 0) + 1
        context['pair_history_json'] = json.dumps(pair_history)

        return context


class PerformShuffleView(AdministratorMixin, RoundMixin, View):
    """POST endpoint that triggers the auto-shuffle."""

    def post(self, request, *args, **kwargs):
        try:
            perform_speaker_shuffle(self.round)
            messages.success(request, _("Speakers have been shuffled successfully."))
        except Exception as e:
            messages.error(request, _("Shuffle failed: %(error)s") % {'error': str(e)})
            logger.exception("Error performing speaker shuffle")

        from utils.misc import reverse_round
        return HttpResponseRedirect(reverse_round('speaker-shuffle-edit', self.round))


class SaveShuffleView(AdministratorMixin, RoundMixin, View):
    """POST endpoint to save manual speaker-team adjustments from the edit UI."""

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            assignments = data.get('assignments', {})

            with transaction.atomic():
                for speaker_id_str, team_id in assignments.items():
                    Speaker.objects.filter(pk=int(speaker_id_str)).update(team_id=int(team_id))

                # Update the shuffle log
                log_data = {str(k): v for k, v in assignments.items()}
                ShuffleLog.objects.filter(round=self.round).delete()
                ShuffleLog.objects.create(round=self.round, speaker_assignments=log_data)

                # Update pair history for this round
                SpeakerPairHistory.objects.filter(round=self.round).delete()
                team_speakers = {}
                for speaker_id_str, team_id in assignments.items():
                    team_speakers.setdefault(team_id, []).append(int(speaker_id_str))

                history_rows = []
                for team_id, spk_pks in team_speakers.items():
                    if len(spk_pks) == 2:
                        pk1, pk2 = sorted(spk_pks)
                        history_rows.append(SpeakerPairHistory(
                            tournament=self.tournament,
                            speaker1_id=pk1,
                            speaker2_id=pk2,
                            round=self.round,
                        ))
                SpeakerPairHistory.objects.bulk_create(history_rows)

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            logger.exception("Error saving shuffle")
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


class ShuffleHistoryView(AdministratorMixin, RoundMixin, TemplateView):
    """Shows past shuffle results (audit log)."""
    template_name = 'shuffle_history.html'
    page_title = 'Shuffle History'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['shuffle_logs'] = ShuffleLog.objects.filter(
            round__tournament=self.tournament,
        ).select_related('round').order_by('round__seq', '-timestamp')
        return context
