# Generated by Django 4.0.7 on 2023-09-15 07:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('georepo', '0111_rename_data_product_task_id_datasetviewresource_product_task_id_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='dataset',
            name='is_simplified',
            field=models.BooleanField(default=False),
        ),
    ]
