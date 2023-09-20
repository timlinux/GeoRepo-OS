# Generated by Django 4.0.7 on 2023-09-19 16:38

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0067_layeruploadsessionmetadata'),
    ]

    operations = [
        migrations.CreateModel(
            name='LayerUploadSessionActionLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(blank=True, default='', max_length=255, null=True)),
                ('started_at', models.DateTimeField(blank=True, null=True)),
                ('finished_at', models.DateTimeField(blank=True, null=True)),
                ('state_from', models.CharField(blank=True, default='', max_length=255, null=True)),
                ('state_to', models.CharField(blank=True, default='', max_length=255, null=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='dashboard.layeruploadsession')),
            ],
        ),
    ]
