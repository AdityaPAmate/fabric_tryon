from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('fabricapp', '0001_video_jobs')]
    operations = [migrations.AddField(
        model_name='videojob', name='provider_error',
        field=models.JSONField(blank=True, default=dict),
    )]
