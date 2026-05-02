from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("breakqual", "0007_breakcategory_reserve_size_alter_breakingteam_remark"),
    ]

    operations = [
        migrations.AlterField(
            model_name="breakcategory",
            name="rule",
            field=models.CharField(
                choices=[
                    ("standard", "Standard"),
                    ("aida-1996", "AIDA 1996"),
                    ("aida-2016-easters", "AIDA 2016 (Easters)"),
                    ("aida-2016-australs", "AIDA 2016 (Australs)"),
                    ("aida-2019-australs-open", "AIDA 2019 (Australs, Dynamic Cap)"),
                    ("fight-club", "Fight Club (by speakers)"),
                ],
                default="standard",
                help_text='Rule for how the break is calculated (most tournaments should use "Standard")',
                max_length=25,
                verbose_name="rule",
            ),
        ),
    ]
