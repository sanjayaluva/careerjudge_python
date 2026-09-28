"""Report 7 §1-2/§4/§12/§33/§34 — backfill display order values.

Every AssessmentSection and AssessmentQuestion previously defaulted to
order=0 (the create endpoints never set it), so any ordering by "order"
was meaningless and delivered question lists came out jumbled or
reversed. This data migration backfills ``order`` from primary keys,
which preserves the author's creation/assignment order (the order the
client expects per Report 7 §2: "exactly in the order each section,
subsection and questions are assigned").

Sections are numbered per-parent (siblings share a sequence); questions
are numbered per-section. Data-only migration — no schema change.
"""

from django.db import migrations


def backfill_orders(apps, schema_editor):
    AssessmentSection = apps.get_model("assessment", "AssessmentSection")
    AssessmentQuestion = apps.get_model("assessment", "AssessmentQuestion")

    # Sections: consecutive order within each parent (root sections under
    # the same assessment form one sibling group; pk order = creation order).
    for assessment_id in AssessmentSection.objects.values_list(
        "assessment_id", flat=True
    ).distinct():
        for parent_id in [None] + list(
            AssessmentSection.objects.filter(assessment_id=assessment_id)
            .exclude(parent=None)
            .values_list("parent_id", flat=True)
            .distinct()
        ):
            siblings = AssessmentSection.objects.filter(
                assessment_id=assessment_id, parent=parent_id
            ).order_by("id")
            for idx, section in enumerate(siblings, start=1):
                if section.order == 0 or section.order is None:
                    AssessmentSection.objects.filter(id=section.id).update(order=idx)

    # Questions: consecutive order within each section (pk = assignment order).
    for section_id in AssessmentQuestion.objects.values_list("section_id", flat=True).distinct():
        aqs = AssessmentQuestion.objects.filter(section_id=section_id).order_by("id")
        for idx, aq in enumerate(aqs, start=1):
            if aq.order == 0 or aq.order is None:
                AssessmentQuestion.objects.filter(id=aq.id).update(order=idx)


def unbackfill_orders(apps, schema_editor):
    # Irreversible data fix — reversing would corrupt current orders.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("assessment", "0008_psychometricgroupresponse"),
    ]

    operations = [
        migrations.RunPython(backfill_orders, unbackfill_orders),
    ]
