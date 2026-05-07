# Generated migration for ArchiveDocument UUID field
# This adds a UUID field for portability across server instances

from django.db import migrations, models
import uuid


def generate_uuids(apps, schema_editor):
    """Generate UUIDs for all existing ArchiveDocument records."""
    ArchiveDocument = apps.get_model('archive', 'ArchiveDocument')
    
    for doc in ArchiveDocument.objects.all():
        if doc.uuid is None:
            doc.uuid = uuid.uuid4()
            doc.save(update_fields=['uuid'])


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0009_merge_20260506_2347'),
    ]

    operations = [
        # Step 1: Add the uuid field as nullable
        migrations.AddField(
            model_name='archivedocument',
            name='uuid',
            field=models.UUIDField(
                unique=True,
                null=True,
                blank=True,
                editable=False,
                help_text="Unique identifier for portability across server instances"
            ),
        ),
        # Step 2: Backfill UUIDs for existing records
        migrations.RunPython(
            generate_uuids,
            reverse_code=migrations.RunPython.noop  # Can't reverse: UUIDs would be lost
        ),
        # Step 3: Make the field non-nullable
        migrations.AlterField(
            model_name='archivedocument',
            name='uuid',
            field=models.UUIDField(
                unique=True,
                null=False,
                blank=False,
                editable=False,
                help_text="Unique identifier for portability across server instances",
                default=uuid.uuid4,
            ),
        ),
    ]
