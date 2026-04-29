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
