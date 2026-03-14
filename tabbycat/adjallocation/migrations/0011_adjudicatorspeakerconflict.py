import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("adjallocation", "0010_alter_adjudicatoradjudicatorconflict_unique_together_and_more"),
        ("participants", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="AdjudicatorSpeakerConflict",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "adjudicator",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="participants.adjudicator",
                        verbose_name="adjudicator",
                    ),
                ),
                (
                    "speaker",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="participants.speaker",
                        verbose_name="speaker",
                    ),
                ),
            ],
            options={
                "verbose_name": "adjudicator-speaker conflict",
                "verbose_name_plural": "adjudicator-speaker conflicts",
            },
        ),
        migrations.AddConstraint(
            model_name="adjudicatorspeakerconflict",
            constraint=models.UniqueConstraint(
                fields=("adjudicator", "speaker"),
                name="adjallo_adjudicatorspeakerconflict_adjudicator__speaker_uniq",
            ),
        ),
    ]
