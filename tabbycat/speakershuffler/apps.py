from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SpeakerShufflerConfig(AppConfig):
    name = 'speakershuffler'
    verbose_name = _("Speaker Shuffler")
