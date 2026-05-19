# Copyright (C) 2026 Byers Brands, LLC
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.

# Hard refactor: Competing Timelines
# No legacy support. No backfill. No guessing.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('archive', '0007_alter_archivedocument_file_type'),
        ('timeline', '0005_uuid_pk_and_source_fields'),
    ]

    operations = [
        # =====================================================================
        # PURGE LEGACY
        # =====================================================================
        migrations.RemoveField(
            model_name='timelineevent',
            name='supporting_docs',
        ),

        # =====================================================================
        # ALTER EXISTING
        # =====================================================================
        migrations.AlterField(
            model_name='timelineevent',
            name='source_party',
            field=models.CharField(
                choices=[
                    ('CLIENT', 'Client/Plaintiff'),
                    ('OPPOSING', 'Opposing Party/Defendant'),
                    ('NEUTRAL', 'Neutral Third Party'),
                    ('COURT', 'Court'),
                    ('WITNESS', 'Witness'),
                ],
                help_text='Party that created or asserts this event',
                max_length=20,
            ),
        ),

        # =====================================================================
        # ADD NEW FIELDS
        # =====================================================================
        migrations.AddField(
            model_name='timelineevent',
            name='status',
            field=models.CharField(
                choices=[
                    ('UNDISPUTED', 'Undisputed'),
                    ('CONTESTED', 'Contested'),
                    ('REFUTED', 'Refuted'),
                    ('STIPULATED', 'Stipulated'),
                    ('PENDING', 'Pending Review'),
                ],
                default='UNDISPUTED',
                help_text='Status of this event in the competing timeline context',
                max_length=20,
            ),
        ),

        migrations.AddField(
            model_name='timelineevent',
            name='evidence',
            field=models.ManyToManyField(
                blank=True,
                help_text='Documents that support or evidence this event',
                related_name='timeline_events',
                to='archive.ArchiveDocument',
            ),
        ),

        migrations.AddField(
            model_name='timelineevent',
            name='replaces_event',
            field=models.ForeignKey(
                blank=True,
                help_text='Event this is a counter-claim to',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='counter_claims',
                to='timeline.TimelineEvent',
            ),
        ),

        migrations.AddField(
            model_name='timelineevent',
            name='version',
            field=models.PositiveIntegerField(
                default=1,
                help_text='Version number for this event',
            ),
        ),

        migrations.AddField(
            model_name='timelineevent',
            name='created_at',
            field=models.DateTimeField(
                auto_now_add=True,
                help_text='When this event was created',
            ),
        ),

        migrations.AddField(
            model_name='timelineevent',
            name='updated_at',
            field=models.DateTimeField(
                auto_now=True,
                help_text='When this event was last updated',
            ),
        ),

        # =====================================================================
        # UPDATE CONSTRAINTS
        # =====================================================================
        migrations.AlterUniqueTogether(
            name='timelineevent',
            unique_together={('case', 'date', 'event', 'source_party')},
        ),
    ]
