import json
import logging

from django.contrib import messages
from django.db import transaction
from django.forms import ModelChoiceField
from django.http import HttpResponseRedirect, JsonResponse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy
from django.views.generic.base import TemplateView, View

from actionlog.mixins import LogActionMixin
from actionlog.models import ActionLogEntry
from participants.models import Speaker
from tournaments.mixins import RoundMixin, TournamentMixin
from utils.misc import redirect_tournament
from utils.mixins import AdministratorMixin
from utils.views import ModelFormSetView

from .models import ShuffleLog, SpeakerConflict, SpeakerPairHistory
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


class SpeakerConflictsView(LogActionMixin, AdministratorMixin, TournamentMixin, ModelFormSetView):
    """Add/edit speaker-speaker conflicts for Fight Club mode."""

    template_name = 'edit_conflicts.html'
    page_title = gettext_lazy("Speaker-Speaker Conflicts")
    page_emoji = "🔶"
    formset_model = SpeakerConflict
    save_text = gettext_lazy("Save Speaker-Speaker Conflicts")
    action_log_type = ActionLogEntry.ActionType.CONFLICTS_SPEAKER_EDIT

    formset_factory_kwargs = {
        'fields': ('speaker1', 'speaker2'),
        'field_classes': {'speaker1': ModelChoiceField, 'speaker2': ModelChoiceField},
    }

    def get_formset_factory_kwargs(self):
        kwargs = super().get_formset_factory_kwargs()
        kwargs['extra'] = 10
        kwargs['can_delete'] = True
        return kwargs

    def get_formset(self):
        formset = super().get_formset()
        all_speakers = Speaker.objects.filter(
            team__tournament=self.tournament,
        ).select_related('team').order_by('name')
        for form in formset:
            form.fields['speaker1'].queryset = all_speakers
            form.fields['speaker2'].queryset = all_speakers
        return formset

    def get_formset_queryset(self):
        return self.formset_model.objects.filter(
            tournament=self.tournament,
        ).order_by('speaker1__name')

    def get_context_data(self, **kwargs):
        kwargs['save_text'] = self.save_text
        kwargs['can_edit'] = True
        return super().get_context_data(**kwargs)

    def get_success_url(self, *args, **kwargs):
        from utils.misc import reverse_tournament
        return reverse_tournament('importer-simple-index', self.tournament)

    def formset_valid(self, formset):
        # Set tournament on new instances before saving
        for form in formset:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                if form.instance and not form.instance.tournament_id:
                    form.instance.tournament = self.tournament
        result = super().formset_valid(formset)
        nsaved = len(self.instances)
        ndeleted = len(formset.deleted_objects)
        if nsaved > 0:
            messages.success(self.request, _("Saved %(count)d speaker-speaker conflict(s).") % {'count': nsaved})
        if ndeleted > 0:
            messages.success(self.request, _("Deleted %(count)d speaker-speaker conflict(s).") % {'count': ndeleted})
        if nsaved == 0 and ndeleted == 0:
            messages.success(self.request, _("No changes were made to speaker-speaker conflicts."))
        if "add_more" in self.request.POST:
            return redirect_tournament('speakershuffler-conflicts', self.tournament)
        return result
