"""Convert image/file fields from ImageField/FileField to TextField.

The frontend MediaManager uploads media as base64 data URLs or external URLs
inside JSON payloads (not as multipart file uploads). ImageField and FileField
DRF serializer fields reject these string values, and the underlying varchar(100)
column is too short to store base64 data URLs. Switch all four media-related
fields to TextField (no length limit, no URL validation).

null=True is kept on the image fields (matches the original ImageField semantics)
because the frontend sends explicit JSON null for empty image fields, e.g.
{"image_file": null, ...} in the bulk options payload. Without null=True the
INSERT would fail with a database IntegrityError.

Fields changed:
  - Question.image            : ImageField → TextField (blank=True, null=True)
  - ResponseOption.image_file : ImageField → TextField (blank=True, null=True)
  - FlashItem.image_file      : ImageField → TextField (blank=True, null=True)
  - MediaFile.file            : FileField  → TextField (blank=True)
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("question_bank", "0001_initial"),
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
        migrations.AlterField(
            model_name="mediafile",
            name="file",
            field=models.TextField(
                blank=True,
                default="",
                help_text="Media file URL (audio/video) — external URL or base64 data URL.",
                verbose_name="file",
            ),
        ),
    ]
