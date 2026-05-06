# Generated migration for TimelineEvent system source fields

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('timeline', '0007_timelinecollection'),
    ]

    operations = [
        migrations.AddField(
            model_name='timelineevent',
            name='is_system_source',
            field=models.BooleanField(
                default=False,
                help_text='Whether this event comes from an authoritative system source (COURT, NEUTRAL)'
            ),
        ),
        migrations.AddField(
            model_name='timelineevent',
            name='trust_level',
            field=models.PositiveSmallIntegerField(
                choices=[
                    (1, 'Low - Unverified'),
                    (2, 'Medium - User Verified'),
                    (3, 'High - Documented'),
                    (4, 'Very High - Official Record'),
                    (5, 'Maximum - Court Stipulated'),
                ],
                default=3,
                help_text='Trust level from 1 (low) to 5 (maximum)'
            ),
        ),
        # Update existing COURT/NEUTRAL events to have system source
        migrations.RunSQL(
            sql="""
                UPDATE timeline_timelineevent 
                SET is_system_source = TRUE, 
                    trust_level = 5,
                    status = 'STIPULATED'
                WHERE source_party IN ('COURT', 'NEUTRAL');
            """,
            reverse_sql="""
                -- No reverse: these were data corrections
            """
        ),
    ]
