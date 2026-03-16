from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class SpeakerShufflerConfig(AppConfig):
    name = 'speakershuffler'
    verbose_name = _("Speaker Shuffler")

    def ready(self):
        self._install_fight_club_name_descriptors()

    @staticmethod
    def _install_fight_club_name_descriptors():
        """Override Team.short_name and Team.long_name with data descriptors
        that return speaker names in Fight Club mode. This makes every rendering
        path (tables, serializers, template tags, views) show "Alice & Bob"
        instead of the institution-based team name, without patching each path
        individually."""
        from participants.models import Team

        for field_name in ('short_name', 'long_name'):
            original = Team.__dict__[field_name]  # DeferredAttribute

            class FightClubDescriptor:
                """Data descriptor that returns speaker names in Fight Club mode."""
                def __init__(self, orig):
                    self.field = orig.field  # Django ORM needs .field

                def __get__(self, obj, objtype=None):
                    if obj is None:
                        return self
                    fc = obj.__dict__.get('_fc_mode')
                    if fc is None:
                        try:
                            fc = obj.tournament.pref('fight_club_mode')
                        except Exception:
                            fc = False
                        obj.__dict__['_fc_mode'] = fc
                    if fc:
                        speakers = getattr(obj, '_prefetched_objects_cache', {}).get('speaker_set')
                        if speakers is not None and speakers:
                            # Guard: if prefetch has more speakers than
                            # substantive_speakers, it wasn't patched —
                            # fall through to the DB value.
                            max_spk = obj.__dict__.get('_fc_max_spk')
                            if max_spk is None:
                                try:
                                    max_spk = obj.tournament.pref('substantive_speakers')
                                except Exception:
                                    max_spk = 99
                                obj.__dict__['_fc_max_spk'] = max_spk
                            if len(speakers) <= max_spk:
                                return " & ".join(s.name for s in speakers)
                    return obj.__dict__.get(self.field.attname)

                def __set__(self, obj, value):
                    obj.__dict__[self.field.attname] = value

            setattr(Team, field_name, FightClubDescriptor(original))
