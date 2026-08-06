"""Add psychometric option fields: section_tag + forced-choice scores.

Per Report 2 (System Testing & Review Feedback Report 2, 25-07-2026):
  - Common Issue 3: each psychometric option must tag to a section.
    ``section_tag`` is a portable label resolved to an AssessmentSection at
    assessment-assign time.
  - §3/§4: forced-choice scoring is by selection vs non-selection, not a
    single predefined score. ``selection_score`` / ``non_selection_score``
    replace ``predefined_score`` (kept for backward-compat).
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0012_question_sub_question_texts_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="responseoption",
            name="section_tag",
            field=models.CharField(
                blank=True,
                default="",
                help_text=(
                    "Psychometric types: the profile variable / section this option "
                    "feeds into (e.g. 'Leadership'). Resolved to an AssessmentSection "
                    "when the question is attached to an assessment."
                ),
                max_length=100,
                verbose_name="section tag",
            ),
        ),
        migrations.AddField(
            model_name="responseoption",
            name="selection_score",
            field=models.FloatField(
                default=1.0,
                help_text=(
                    "Forced-choice: score posted to this option's section when the "
                    "candidate SELECTS it. Rule: selection_score > non_selection_score "
                    ">= 0. Default 1."
                ),
                verbose_name="selection score",
            ),
        ),
        migrations.AddField(
            model_name="responseoption",
            name="non_selection_score",
            field=models.FloatField(
                default=0.0,
                help_text=(
                    "Forced-choice: score posted to this option's section when the "
                    "candidate does NOT select it. Must be >= 0 and < selection_score. "
                    "Default 0."
                ),
                verbose_name="non-selection score",
            ),
        ),
        migrations.AlterField(
            model_name="responseoption",
            name="predefined_score",
            field=models.FloatField(
                default=1.0,
                help_text=(
                    "Deprecated for forced-choice (kept for backward-compat). "
                    "Use selection_score / non_selection_score instead."
                ),
                verbose_name="predefined score",
            ),
        ),
    ]
