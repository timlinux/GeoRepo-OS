# Generated by Django 4.0.7 on 2023-09-13 01:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0064_layerfile_attributes'),
    ]

    operations = [
        migrations.CreateModel(
            name='EntityUploadStatusLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('logs', models.JSONField(blank=True, default=dict, help_text='Logs of upload', null=True)),
                ('entity_upload_status', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.entityuploadstatus')),
                ('layer_upload_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.layeruploadsession')),
                ('parent_log', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='dashboard.entityuploadstatuslog')),
            ],
        ),
    ]
