from django.urls import include, path

from . import views

urlpatterns = [
    path('round/<int:round_seq>/', include([
        path('edit/',
            views.EditSpeakerShuffleView.as_view(),
            name='speaker-shuffle-edit'),
        path('perform/',
            views.PerformShuffleView.as_view(),
            name='speaker-shuffle-perform'),
        path('save/',
            views.SaveShuffleView.as_view(),
            name='speaker-shuffle-save'),
        path('history/',
            views.ShuffleHistoryView.as_view(),
            name='speaker-shuffle-history'),
    ])),
    path('conflicts/',
        views.SpeakerConflictsView.as_view(),
        name='speakershuffler-conflicts'),
]
