# Generated by Django 4.0.7 on 2023-09-29 16:26

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0121_adminleveltilingconfig_georepo_adm_dataset_28b2dd_idx_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='geographicalentity',
            name='bbox',
            field=models.CharField(blank=True, default='', help_text='Geometry bounding box', max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='geographicalentity',
            name='centroid',
            field=models.CharField(blank=True, default='', help_text='Geometry centroid using ST_PointOnSurface', max_length=255, null=True),
        ),
    ]
