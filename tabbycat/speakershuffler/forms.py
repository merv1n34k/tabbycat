from django import forms
from django.utils.translation import gettext_lazy as _

from tournaments.models import Round


class DirectoryInput(forms.ClearableFileInput):
    """File input widget that opens the OS directory picker."""
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        default_attrs = {'webkitdirectory': '', 'directory': '', 'multiple': ''}
        if attrs:
            default_attrs.update(attrs)
        super().__init__(attrs=default_attrs)


class MultiFileField(forms.FileField):
    """FileField that accepts multiple files from a directory input."""

    def clean(self, data, initial=None):
        if not data or data == []:
            if self.required:
                raise forms.ValidationError(self.error_messages['required'])
            return []
        if not isinstance(data, (list, tuple)):
            data = [data]
        return data


class GenerateSlidesForm(forms.Form):
    round = forms.ModelChoiceField(
        queryset=Round.objects.none(),
        label=_("Round"),
        empty_label=_("(select a round)"),
    )
    photos = MultiFileField(
        label=_("Photos directory"),
        help_text=_("Click to select the folder containing speaker photos."),
        widget=DirectoryInput(),
    )
    template_file = forms.FileField(
        label=_("Template image"),
        help_text=_("Click to select the template PNG file."),
        widget=forms.ClearableFileInput(attrs={'accept': 'image/png'}),
    )

    def __init__(self, tournament, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['round'].queryset = tournament.round_set.filter(
            stage=Round.Stage.PRELIMINARY,
        ).exclude(
            draw_status=Round.Status.NONE,
        ).order_by('seq')
