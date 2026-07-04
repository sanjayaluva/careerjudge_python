"""Add question_title field to Question model.

The question_title is a mandatory short title that identifies a question
in lists and previews — separate from question_text_1 (the actual question
text shown to candidates). This makes it easier to identify questions in
the question bank list without reading the full question text.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0004_question_flash_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="question_title",
            field=models.CharField(
                help_text="Short title that identifies this question in lists and previews. Required.",
                max_length=255,
                verbose_name="question title",
            ),
        ),
    ]
