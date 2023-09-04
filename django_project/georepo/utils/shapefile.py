import fiona
import zipfile
import os
import subprocess
from django.core.files.storage import default_storage
from django.conf import settings
from django.core.files.uploadedfile import (
    InMemoryUploadedFile
)
from georepo.models import (
    DatasetView,
    DatasetViewResource
)
from georepo.utils.exporter_base import (
    DatasetViewExporterBase
)
from georepo.utils.fiona_utils import (
    list_layers_shapefile,
    delete_tmp_shapefile,
    open_collection_by_file
)

# buffer the data before writing/flushing to file
SHAPEFILE_RECORDS_BUFFER_TX = 400
SHAPEFILE_RECORDS_BUFFER = 800

GENERATED_FILES = ['.shp', '.dbf', '.shx', '.cpg', '.prj']


def extract_shapefile_attributes(layer_file):
    """
    Load and read shape file, and returns all the attributes
    :param layer_file_path: path of the layer file
    :return: list of attributes, e.g. ['id', 'name', ...]
    """
    attrs = []
    with open_collection_by_file(layer_file, 'SHAPEFILE') as collection:
        try:
            attrs = next(iter(collection))["properties"].keys()
        except (KeyError, IndexError):
            pass
        delete_tmp_shapefile(collection.path)
    return attrs


def get_shape_file_feature_count(layer_file):
    """
    Get Feature count in shape file
    """
    feature_count = 0
    with open_collection_by_file(layer_file, 'SHAPEFILE') as collection:
        feature_count = len(collection)
        delete_tmp_shapefile(collection.path)
    return feature_count


def store_zip_memory_to_temp_file(file_obj: InMemoryUploadedFile):
    tmp_path = os.path.join(settings.MEDIA_ROOT, 'tmp')
    if not os.path.exists(tmp_path):
        os.makedirs(tmp_path)
    path = 'tmp/' + file_obj.name
    with default_storage.open(path, 'wb+') as destination:
        for chunk in file_obj.chunks():
            destination.write(chunk)
    return path


def validate_shapefile_zip(layer_file_path: any):
    """
    Validate if shapefile zip has correct necessary files
    Note: fiona will throw exception only if dbf or shx is missing
    if there are 2 layers inside the zip, and 1 of them is invalid,
    then fiona will only return 1 layer
    """
    layers = list_layers_shapefile(layer_file_path)
    is_valid = len(layers) > 0
    error = []
    names = []
    with zipfile.ZipFile(layer_file_path, 'r') as zipFile:
        names = zipFile.namelist()
    shp_files = [n for n in names if n.endswith('.shp')]
    shx_files = [n for n in names if n.endswith('.shx')]
    dbf_files = [n for n in names if n.endswith('.dbf')]

    if is_valid:
        for filename in layers:
            if f'{filename}.shp' not in shp_files:
                error.append(f'{filename}.shp')
            if f'{filename}.shx' not in shx_files:
                error.append(f'{filename}.shx')
            if f'{filename}.dbf' not in dbf_files:
                error.append(f'{filename}.dbf')
    else:
        distinct_files = (
            [
                os.path.splitext(shp)[0] for shp in shp_files
            ] +
            [
                os.path.splitext(shx)[0] for shx in shx_files
            ] +
            [
                os.path.splitext(dbf)[0] for dbf in dbf_files
            ]
        )
        distinct_files = list(set(distinct_files))
        if len(distinct_files) == 0:
            error.append('No required .shp file')
        else:
            for filename in distinct_files:
                if f'{filename}.shp' not in shp_files:
                    error.append(f'{filename}.shp')
                if f'{filename}.shx' not in shx_files:
                    error.append(f'{filename}.shx')
                if f'{filename}.dbf' not in dbf_files:
                    error.append(f'{filename}.dbf')
    is_valid = is_valid and len(error) == 0
    return is_valid, error


class ShapefileViewExporter(DatasetViewExporterBase):
    output = 'shapefile'

    def get_base_output_dir(self) -> str:
        return settings.SHAPEFILE_FOLDER_OUTPUT

    def write_entities(self, schema, entities, context,
                       exported_name, tmp_output_dir,
                       tmp_metadata_file, resource) -> str:
        suffix = '.shp'
        shape_file = os.path.join(
            tmp_output_dir,
            exported_name
        ) + suffix
        geojson_file = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            str(resource.uuid),
            exported_name
        ) + '.geojson'
        # use ogr to convert from geojson to shapefile
        command_list = (
            [
                'ogr2ogr',
                '-f',
                'ESRI Shapefile',
                '-overwrite',
                '-gt',
                '200',
                '-skipfailures',
                shape_file,
                geojson_file
            ]
        )
        subprocess.run(command_list)
        # zip all the files
        zip_file_path = os.path.join(
            tmp_output_dir,
            f'{exported_name}'
        ) + '.zip'
        with zipfile.ZipFile(
                zip_file_path, 'w', zipfile.ZIP_DEFLATED) as archive:
            for suffix in GENERATED_FILES:
                shape_file = os.path.join(
                    tmp_output_dir,
                    exported_name
                ) + suffix
                if not os.path.exists(shape_file):
                    continue
                archive.write(
                    shape_file,
                    arcname=exported_name + suffix
                )
                os.remove(shape_file)
            # add metadata
            archive.write(
                tmp_metadata_file,
                arcname=exported_name + '.xml'
            )
            os.remove(tmp_metadata_file)
        return zip_file_path


def generate_view_shapefile(dataset_view: DatasetView,
                            view_resource: DatasetViewResource = None):
    """
    Extract shape file from dataset_view and then save it to
    shapefile dataset_view folder
    :param dataset: dataset_view object
    """
    exporter = ShapefileViewExporter(dataset_view,
                                     view_resource=view_resource)
    exporter.init_exporter()
    exporter.run()
