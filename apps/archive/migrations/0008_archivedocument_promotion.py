# Generated migration for ArchiveDocument promotion fields

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0007_alter_archivedocument_file_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='archivedocument',
            name='is_promoted',
            field=models.BooleanField(
                default=False,
                help_text='Whether this document has been promoted to formal evidence'
            ),
        ),
        migrations.AddField(
            model_name='archivedocument',
            name='promoted_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                help_text='When this document was promoted to formal evidence'
            ),
        ),
    ]
