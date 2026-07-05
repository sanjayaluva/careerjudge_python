"""Add shape_type, is_correct, radius, points to HotspotArea.

Supports the hotspot shape designer: rectangle, circle, and custom polygon.
Previously HotspotArea only stored x, y, width_px, height_px (rectangle only).
Now it also stores:
- shape_type: RECTANGLE / CIRCLE / POLYGON
- is_correct: whether this area is a correct answer (green) or distractor (red)
- radius: for CIRCLE shapes (distance from x,y center)
- points: JSON array of {x, y} for POLYGON shapes
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0005_question_title"),
    ]

    operations = [
        migrations.AddField(
            model_name="hotspotarea",
            name="shape_type",
            field=models.CharField(
                choices=[("RECTANGLE", "Rectangle"), ("CIRCLE", "Circle"), ("POLYGON", "Polygon")],
                default="RECTANGLE",
                max_length=20,
                verbose_name="shape type",
            ),
        ),
        migrations.AddField(
            model_name="hotspotarea",
            name="is_correct",
            field=models.BooleanField(default=True, verbose_name="is correct"),
        ),
        migrations.AddField(
            model_name="hotspotarea",
            name="radius",
            field=models.PositiveIntegerField(blank=True, null=True, verbose_name="radius (px)"),
        ),
        migrations.AddField(
            model_name="hotspotarea",
            name="points",
            field=models.JSONField(blank=True, null=True, verbose_name="polygon points"),
        ),
        migrations.AlterField(
            model_name="hotspotarea",
            name="width_px",
            field=models.PositiveIntegerField(default=0, verbose_name="width (px)"),
        ),
        migrations.AlterField(
            model_name="hotspotarea",
            name="height_px",
            field=models.PositiveIntegerField(default=0, verbose_name="height (px)"),
        ),
    ]
