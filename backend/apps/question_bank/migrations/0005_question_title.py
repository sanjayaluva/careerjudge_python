"""Add question_title field to Question model.

The question_title is a mandatory short title that identifies a question
in lists and previews — separate from question_text_1 (the actual question
text shown to candidates). This makes it easier to identify questions in
the question bank list without reading the full question text.

Uses a temporary default of "" so existing rows (which don't have a title)
get populated with an empty string during migration. The default is removed
after migration (preserve_default=False) — new questions must provide a title.
"""

from django.db import migrations, models


def populate_question_titles(apps, schema_editor):
    """Set question_title to the first 255 chars of question_text_1 for existing questions."""
    Question = apps.get_model("question_bank", "Question")
    for q in Question.objects.all():
        if not q.question_title:
            q.question_title = (q.question_text_1 or "Untitled")[:255]
            q.save(update_fields=["question_title"])


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0004_question_flash_order"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="question_title",
            field=models.CharField(
                default="",
                help_text="Short title that identifies this question in lists and previews. Required.",
                max_length=255,
                verbose_name="question title",
            ),
            preserve_default=False,
        ),
        migrations.RunPython(populate_question_titles, migrations.RunPython.noop),
    ]
