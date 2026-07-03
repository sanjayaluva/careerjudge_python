"""Add null=True to image/file TextField fields.

Migration 0002 (from commit 44740ab) converted the four media fields from
ImageField/FileField to TextField but only set blank=True (no null=True).
DRF's allow_null=True serializer field accepts None and passes it through
to the model, but the DB column rejected NULL inserts → IntegrityError →
500 server_error on bulk options save when the frontend sent
{"image_file": null, ...}.

This migration adds null=True to the three image fields (Question.image,
ResponseOption.image_file, FlashItem.image_file). MediaFile.file is left
as NOT NULL because the frontend always sends a value for media files
(audio/video URLs are required when media_type is provided).

This is a separate migration (not an edit to 0002) because 0002 was
already applied to the dev database in the previous deploy. Django tracks
applied migrations by name, so editing 0002 in-place would not re-run it.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0002_image_file_fields_to_text"),
    ]

    operations = [
        migrations.AlterField(
            model_name="question",
            name="image",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Question image as an external URL or base64 data URL.",
                null=True,
                verbose_name="image",
            ),
        ),
        migrations.AlterField(
            model_name="responseoption",
            name="image_file",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Option image as an external URL or base64 data URL.",
                null=True,
                verbose_name="image file",
            ),
        ),
        migrations.AlterField(
            model_name="flashitem",
            name="image_file",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Flash image as an external URL or base64 data URL.",
                null=True,
                verbose_name="image file",
            ),
        ),
    ]
