# Generated by Django 4.0.7 on 2023-08-01 06:39

import core.models.preferences
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_sitepreferences_base_url_help_page'),
    ]

    operations = [
        migrations.AlterField(
            model_name='sitepreferences',
            name='api_config',
            field=models.JSONField(blank=True, default=core.models.preferences.default_api_config),
        ),
        migrations.AlterField(
            model_name='sitepreferences',
            name='default_admin_emails',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='sitepreferences',
            name='default_geometry_checker_params',
            field=models.JSONField(blank=True, default=core.models.preferences.default_geometry_checker_params),
        ),
        migrations.AlterField(
            model_name='sitepreferences',
            name='default_public_groups',
            field=models.JSONField(blank=True, default=core.models.preferences.default_public_groups),
        ),
        migrations.AlterField(
            model_name='sitepreferences',
            name='level_names_template',
            field=models.JSONField(blank=True, default=list),
        ),
        migrations.AlterField(
            model_name='sitepreferences',
            name='metadata_xml_config',
            field=models.JSONField(blank=True, default=core.models.preferences.default_metadata_xml_config),
        ),
        migrations.AlterField(
            model_name='sitepreferences',
            name='tile_configs_template',
            field=models.JSONField(blank=True, default=list),
        ),
    ]
