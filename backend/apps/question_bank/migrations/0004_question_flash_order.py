"""Add flash_order field to Question model.

Supports customizing the presentation order of flash items:
- SEQUENCE: items shown in the order they were entered (default, current behavior)
- RANDOM: items shuffled randomly at presentation time
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0003_image_fields_add_null_true"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="flash_order",
            field=models.CharField(
                choices=[("SEQUENCE", "Sequence (as entered)"), ("RANDOM", "Random (shuffled)")],
                default="SEQUENCE",
                help_text="For flash types 1e/1f/2c/2d — order in which flash items are presented",
                max_length=10,
                verbose_name="flash order",
            ),
        ),
    ]
