# Migration for TimelineCollection model

from django.db import migrations, models
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('timeline', '0006_competing_timelines'),
    ]

    operations = [
        migrations.CreateModel(
            name='TimelineCollection',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text='Name of this collection', max_length=200)),
                ('description', models.TextField(blank=True, help_text='Description of the collection\'s purpose')),
                ('is_public', models.BooleanField(default=False, help_text='Whether this collection is visible to other users of the case')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('case', models.ForeignKey(help_text='Case this collection belongs to', on_delete=models.CASCADE, related_name='collections', to='core.case')),
                ('created_by', models.ForeignKey(help_text='User who created this collection', on_delete=models.CASCADE, related_name='timeline_collections', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
                'verbose_name': 'Timeline Collection',
                'verbose_name_plural': 'Timeline Collections',
                'unique_together': {('name', 'case')},
            },
        ),
        migrations.AddField(
            model_name='timelinecollection',
            name='events',
            field=models.ManyToManyField(blank=True, help_text='Timeline events in this collection', related_name='collections', to='timeline.TimelineEvent'),
        ),
    ]
