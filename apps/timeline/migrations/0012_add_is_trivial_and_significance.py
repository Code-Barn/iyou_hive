from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('timeline', '0011_add_last_printed_citation'),
    ]

    operations = [
        migrations.AddField(
            model_name='timelineevent',
            name='is_trivial',
            field=models.BooleanField(
                default=False,
                help_text='If True, this event is considered noise and can be filtered out',
            ),
        ),
        migrations.AddField(
            model_name='timelineevent',
            name='significance',
            field=models.PositiveSmallIntegerField(
                default=3,
                choices=[
                    (1, 'Minimal'),
                    (2, 'Low'),
                    (3, 'Normal'),
                    (4, 'Important'),
                    (5, 'Critical'),
                ],
                help_text='Significance level from 1 (minimal) to 5 (critical)',
            ),
        ),
    ]
