from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('participants', '0001_initial'),
        ('tournaments', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='SpeakerPairHistory',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournaments.tournament', verbose_name='tournament')),
                ('speaker1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pair_history_as_first', to='participants.speaker', verbose_name='speaker 1')),
                ('speaker2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='pair_history_as_second', to='participants.speaker', verbose_name='speaker 2')),
                ('round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournaments.round', verbose_name='round')),
            ],
            options={
                'verbose_name': 'speaker pair history',
                'verbose_name_plural': 'speaker pair histories',
            },
        ),
        migrations.AddConstraint(
            model_name='speakerpairhistory',
            constraint=models.UniqueConstraint(fields=('speaker1', 'speaker2', 'round'), name='unique_speaker_pair_per_round'),
        ),
        migrations.CreateModel(
            name='ShuffleLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('timestamp', models.DateTimeField(auto_now_add=True, verbose_name='timestamp')),
                ('speaker_assignments', models.JSONField(help_text='Mapping of speaker ID to team ID', verbose_name='speaker assignments')),
                ('round', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournaments.round', verbose_name='round')),
            ],
            options={
                'verbose_name': 'shuffle log',
                'verbose_name_plural': 'shuffle logs',
                'ordering': ['-timestamp'],
            },
        ),
        migrations.CreateModel(
            name='SpeakerConflict',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tournament', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='tournaments.tournament', verbose_name='tournament')),
                ('speaker1', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conflict_as_first', to='participants.speaker', verbose_name='speaker 1')),
                ('speaker2', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='conflict_as_second', to='participants.speaker', verbose_name='speaker 2')),
            ],
            options={
                'verbose_name': 'speaker conflict',
                'verbose_name_plural': 'speaker conflicts',
            },
        ),
        migrations.AddConstraint(
            model_name='speakerconflict',
            constraint=models.UniqueConstraint(fields=('speaker1', 'speaker2'), name='unique_speaker_conflict'),
        ),
    ]
