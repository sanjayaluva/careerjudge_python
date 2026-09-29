import re

from django.db import migrations

POINT = re.compile(r"^Point (\d+)$")


def forwards(apps, schema_editor):
    """Report 7 #29/#30: every update of a Standard Rating Scale question
    re-added its "Point n" legend options (5 -> 80). Keep the most recent
    legend per point (the last save, i.e. the author's latest text) and
    remove the stale copies and any points beyond the scale."""
    ResponseOption = apps.get_model("question_bank", "ResponseOption")
    Question = apps.get_model("question_bank", "Question")
    for q in Question.objects.filter(question_type="STANDARD_RATING_SCALE").only(
        "id", "rating_scale_points"
    ):
        points = q.rating_scale_points or 5
        keep = {}
        stale = []
        for opt in ResponseOption.objects.filter(question_id=q.id).order_by("-id"):
            m = POINT.match(opt.label or "")
            if not m:
                continue
            n = int(m.group(1))
            if n > points or n in keep:
                stale.append(opt.id)
            else:
                keep[n] = opt.id
        if stale:
            ResponseOption.objects.filter(id__in=stale).delete()


class Migration(migrations.Migration):
    dependencies = [("question_bank", "0020_fix_type_fixed_scoring")]

    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
