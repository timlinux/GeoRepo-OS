# Generated by Django 4.0.7 on 2023-08-16 04:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0060_alter_batchreview_processed_ids_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            """create or replace function GeomTransformMercator(geom geometry)
                returns geometry
                language plpgsql immutable as
            $func$
            declare
                env geometry;
            begin
                env := ST_MakeEnvelope(-180, -85.0511287798066, 180, 85.0511287798066, 4326);
                if ST_Covers(env, geom) then
                    return ST_Transform(geom, 3857);
                else
                    return ST_Transform(ST_Intersection(env, geom), 3857);
                end if;
            end;
            $func$;""",
            reverse_sql="""drop function if exists
                GeomTransformMercator(geom geometry) restrict;""",
            elidable=False
        )
    ]
