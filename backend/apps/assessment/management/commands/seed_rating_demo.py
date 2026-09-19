"""Seed a published psychometric assessment with a continuous rating section.

Used to visually verify QT-3 (multi_question_continuous rating scroll). Creates a
set of STANDARD_RATING_SCALE questions in one section of a published assessment so
a candidate can start a session and see the continuous-scroll screen.
"""

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.assessment.models import Assessment, AssessmentQuestion, AssessmentSection
from apps.question_bank.models import Question


class Command(BaseCommand):
    help = "Seed a published rating assessment for the QT-3 continuous-scroll demo."

    def handle(self, *args, **opts):
        author = User.objects.filter(email="psychometrician@demo.careerjudge.pp.ua").first()

        Assessment.objects.filter(title="QT-3 Rating Demo").delete()
        Question.objects.filter(question_id_label__startswith="QT3-").delete()

        statements = [
            "I enjoy solving complex problems.",
            "I prefer working in a team rather than alone.",
            "I stay calm under pressure.",
            "I like to plan ahead before acting.",
            "I am comfortable speaking in front of a group.",
            "I pay close attention to small details.",
            "I adapt quickly when plans change.",
            "I enjoy learning new skills.",
            "I find it easy to make decisions.",
            "I like taking on leadership roles.",
            "I am motivated by challenging goals.",
            "I prefer a structured, predictable routine.",
            "I enjoy meeting new people.",
            "I persevere even when a task is difficult.",
            "I consider other people's feelings before acting.",
            "I like to weigh all options before deciding.",
            "I stay organised in my daily work.",
            "I am open to feedback and criticism.",
            "I enjoy competitive situations.",
            "I follow through on my commitments.",
        ]
        qs = []
        for i, text in enumerate(statements, 1):
            q = Question.objects.create(
                question_type="STANDARD_RATING_SCALE",
                scoring_type="RATING",
                question_id_label=f"QT3-{i}",
                question_title=f"Rating statement {i}",
                question_text_1=f"<p>{text}</p>",
                difficulty_level="Medium",
                cognitive_level="Understanding",
                rating_scale_points=5,
                rating_direction="FORWARD",
                status="confirmed",
                is_active=True,
                created_by=author,
            )
            qs.append(q)

        a = Assessment.objects.create(
            title="QT-3 Rating Demo",
            assessment_type="psychometric",
            status="published",
            created_by=author,
        )
        sec = AssessmentSection.objects.create(
            assessment=a, title="Personality", description="", level=1, order=1
        )
        for j, q in enumerate(qs, 1):
            AssessmentQuestion.objects.create(section=sec, question=q, order=j)

        self.stdout.write(
            self.style.SUCCESS(
                f"Created published assessment id={a.id} with {len(qs)} rating questions "
                f"in one section."
            )
        )
        self.stdout.write(f"ASSESSMENT_ID={a.id}")
