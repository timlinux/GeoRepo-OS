# Generated by Django 4.0.7 on 2023-09-26 08:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0074_remove_layeruploadsessionactionlog_state_from_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='layeruploadsession',
            name='source',
            field=models.CharField(blank=True, db_index=True, default='', max_length=255),
        ),
    ]
