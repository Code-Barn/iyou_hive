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
