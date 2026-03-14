from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('speakershuffler', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='shufflelog',
            name='team_names',
            field=models.JSONField(blank=True, default=dict, help_text='Mapping of team ID to team name for this round', verbose_name='team names'),
        ),
    ]
