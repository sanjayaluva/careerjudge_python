"""Convert image/file fields from ImageField/FileField to TextField.

The frontend MediaManager uploads media as base64 data URLs or external URLs
inside JSON payloads (not as multipart file uploads). ImageField and FileField
DRF serializer fields reject these string values, and the underlying varchar(100)
column is too short to store base64 data URLs. Switch all four media-related
fields to TextField (no length limit, no URL validation).

Fields changed:
  - Question.image           : ImageField → TextField
  - ResponseOption.image_file : ImageField → TextField
  - FlashItem.image_file     : ImageField → TextField
  - MediaFile.file           : FileField  → TextField
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
                help_text="Question image as an external URL or base64 data URL.",
                verbose_name="image",
            ),
        ),
        migrations.AlterField(
            model_name="responseoption",
            name="image_file",
            field=models.TextField(
                blank=True,
                help_text="Option image as an external URL or base64 data URL.",
                verbose_name="image file",
            ),
        ),
        migrations.AlterField(
            model_name="flashitem",
            name="image_file",
            field=models.TextField(
                blank=True,
                help_text="Flash image as an external URL or base64 data URL.",
                verbose_name="image file",
            ),
        ),
        migrations.AlterField(
            model_name="mediafile",
            name="file",
            field=models.TextField(
                help_text="Media file URL (audio/video) — external URL or base64 data URL.",
                verbose_name="file",
            ),
        ),
    ]
