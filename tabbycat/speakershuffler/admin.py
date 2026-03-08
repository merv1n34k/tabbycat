from django.contrib import admin

from .models import ShuffleLog, SpeakerConflict, SpeakerPairHistory


@admin.register(SpeakerPairHistory)
class SpeakerPairHistoryAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'speaker1', 'speaker2', 'round')
    list_filter = ('tournament', 'round')


@admin.register(ShuffleLog)
class ShuffleLogAdmin(admin.ModelAdmin):
    list_display = ('round', 'timestamp')
    list_filter = ('round__tournament',)
    readonly_fields = ('speaker_assignments',)


@admin.register(SpeakerConflict)
class SpeakerConflictAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'speaker1', 'speaker2')
    list_filter = ('tournament',)
