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
        ('core', '0002_add_3layer_architecture'),
    ]

    operations = [
        migrations.AddField(
            model_name='wikipage',
            name='category',
            field=models.CharField(
                choices=[('VERIFIED', 'Stipulated/Verified'), ('CONTESTED', 'Contested Allegation')],
                default='CONTESTED',
                max_length=20,
                help_text="Whether the content is Stipulated/Verified or Contested"
            ),
        ),
    ]
