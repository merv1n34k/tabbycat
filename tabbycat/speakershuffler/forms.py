from pathlib import Path

from django import forms
from django.utils.translation import gettext_lazy as _

from tournaments.models import Round


class GenerateSlidesForm(forms.Form):
    round = forms.ModelChoiceField(
        queryset=Round.objects.none(),
        label=_("Round"),
        empty_label=_("(select a round)"),
    )
    photos_dir = forms.CharField(
        label=_("Photos directory"),
        help_text=_("Absolute path to the directory containing speaker photos on the server."),
    )
    template_path = forms.CharField(
        label=_("Template image"),
        help_text=_("Absolute path to the template PNG file on the server."),
    )

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['round'].queryset = tournament.round_set.filter(
            stage=Round.Stage.PRELIMINARY,
        ).exclude(
            draw_status=Round.Status.NONE,
        ).order_by('seq')

    def clean_photos_dir(self):
        value = self.cleaned_data['photos_dir']
        p = Path(value)
        if not p.is_dir():
            raise forms.ValidationError(_("Directory does not exist: %(path)s") % {'path': value})
        return value

    def clean_template_path(self):
        value = self.cleaned_data['template_path']
        p = Path(value)
        if not p.is_file():
            raise forms.ValidationError(_("File does not exist: %(path)s") % {'path': value})
        return value
