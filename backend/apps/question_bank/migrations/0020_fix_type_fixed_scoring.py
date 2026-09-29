from django.db import migrations

# 00_question_types_spec / 00_scoring_rules fix the scoring mode for these
# types. Questions saved with another mode (e.g. a 2b saved as "Binary")
# showed the wrong label on results (Report 7 #24); the scorer now applies
# the signed mode regardless, and this aligns the stored value with it.
FIXED = {
    "FITB_SINGLE": "BINARY_FUZZY",
    "FITB_MULTI_FIELD": "PARTIAL",
    "FITB_WORD_FLASH_MULTI": "PARTIAL",
    "FITB_IMAGE_FLASH_MULTI": "PARTIAL",
    "MATCH_FOLLOWING": "PARTIAL",
}


def forwards(apps, schema_editor):
    Question = apps.get_model("question_bank", "Question")
    for qtype, mode in FIXED.items():
        Question.objects.filter(question_type=qtype).exclude(scoring_type=mode).update(
            scoring_type=mode
        )


class Migration(migrations.Migration):
    dependencies = [("question_bank", "0019_alter_question_question_type")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
