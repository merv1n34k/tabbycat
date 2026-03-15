from django.utils.html import escape
from rest_framework import serializers

from .models import Adjudicator, Institution, Speaker, SpeakerCategory, Team


class SpeakerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Speaker
        fields = ('id', 'name', 'gender')


class SpeakerCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SpeakerCategory
        fields = ('name',)


class InstitutionSerializer(serializers.ModelSerializer):
    region = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Institution
        fields = ('id', 'name', 'code', 'region')


class AdjudicatorSerializer(serializers.ModelSerializer):
    institution = serializers.PrimaryKeyRelatedField(read_only=True)
    name = serializers.SerializerMethodField(read_only=True)

    def get_name(self, obj):
        return escape(obj.name)

    class Meta:
        model = Adjudicator
        fields = ('id', 'name', 'gender', 'institution')


class TeamSerializer(serializers.ModelSerializer):
    institution = serializers.PrimaryKeyRelatedField(read_only=True)
    speakers = SpeakerSerializer(read_only=True, many=True)
    points = serializers.SerializerMethodField(read_only=True)
    break_categories = serializers.PrimaryKeyRelatedField(read_only=True, many=True)
    short_name = serializers.SerializerMethodField(read_only=True)
    long_name = serializers.SerializerMethodField(read_only=True)

    def _fight_club_name(self, obj):
        speakers = getattr(obj, '_prefetched_objects_cache', {}).get('speaker_set')
        if speakers is None:
            speakers = obj.speaker_set.all()
        return " & ".join(s.name for s in speakers) if speakers else obj.short_name

    def get_short_name(self, obj):
        if self.context.get('fight_club_mode'):
            return self._fight_club_name(obj)
        return obj.short_name

    def get_long_name(self, obj):
        if self.context.get('fight_club_mode'):
            return self._fight_club_name(obj)
        return obj.long_name

    def get_points(self, obj):
        return obj.points_count

    class Meta:
        model = Team
        fields = ('id', 'short_name', 'long_name', 'code_name', 'points',
                  'institution', 'speakers', 'break_categories')
