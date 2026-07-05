"""Add image_width and image_height to Question.

Stores the image dimensions at the time hotspot shapes were drawn.
Used to scale shapes proportionally when the image is displayed at
a different size on the detail page or at delivery time.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0006_hotspot_shapes"),
    ]

    operations = [
        migrations.AddField(
            model_name="question",
            name="image_width",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Width of the image when hotspot shapes were drawn. Used to scale shapes.",
                verbose_name="image width (px)",
            ),
        ),
        migrations.AddField(
            model_name="question",
            name="image_height",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                help_text="Height of the image when hotspot shapes were drawn. Used to scale shapes.",
                verbose_name="image height (px)",
            ),
        ),
    ]
