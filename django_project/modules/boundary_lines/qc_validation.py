from typing import Tuple
import csv
import json
import uuid
from io import StringIO

import fiona
import logging

from core.celery import app
from django.contrib.gis.geos import (
    GEOSGeometry
)
from django.core.files.base import ContentFile
from django.db import IntegrityError
from django.db.models import IntegerField, Max
from django.db.models.functions import Cast

from dashboard.models.layer_upload_session import LayerUploadSession
from dashboard.models import LayerFile, ERROR, SHAPEFILE
from dashboard.models.entity_upload import EntityUploadStatus, VALID
from georepo.models.dataset import Dataset
from georepo.models.entity import GeographicalEntity, EntityId
from modules.boundary_lines.error_type import (
    ErrorType,
    ALLOWABLE_ERROR_TYPES,
    SUPERADMIN_BYPASS_ERROR
)
from georepo.models.boundary_type import BoundaryType
from georepo.utils.layers import check_valid_value, get_feature_value
from georepo.utils.unique_code import generate_unique_code

logger = logging.getLogger(__name__)

INTERNAL_CODE_DIGITS = 8
LEVEL = 'Level'
ERROR_CHECK = '1'


def run_validation(entity_upload: EntityUploadStatus):
    logger.info('validate boundary_lines')
    layer_files = LayerFile.objects.annotate(
        level_int=Cast('level', IntegerField())
    ).filter(
        layer_upload_session=entity_upload.upload_session
    ).order_by('level_int')

    dataset = entity_upload.upload_session.dataset
    revision = 1

    # find latest revision in current dataset
    max_revision = GeographicalEntity.objects.filter(
        dataset=dataset,
        is_approved=True
    ).aggregate(Max('revision_number'))['revision_number__max']
    if max_revision:
        revision = max_revision + 1
    entity_upload.revision_number = revision
    entity_upload.save()

    validation_summaries = []
    error_summaries = []
    for layer_file in layer_files:
        level = int(layer_file.level)
        level_error_report = {
            LEVEL: level,
            'Boundary Lines': f'Level {level}',
        }
        for error_type in ErrorType:
            level_error_report[error_type.value] = 0
        layer_file_path = layer_file.layer_file.path
        if layer_file.layer_type == SHAPEFILE:
            layer_file_path = f'zip://{layer_file.layer_file.path}'
        with fiona.open(layer_file_path, encoding='utf-8') as layer:
            layer_index = 0
            for feature_idx, feature in enumerate(layer):
                layer_index += 1
                error_found = False
                layer_error = {
                    LEVEL: level,
                }
                for error_type in ErrorType:
                    layer_error[error_type.value] = ''
                logger.info(f'Validating Level {level} - Index {layer_index}')
                # build default/internal code
                internal_code = (
                    f'{str(feature_idx + 1).zfill(INTERNAL_CODE_DIGITS)}'
                )
                # create geom
                geom_str = json.dumps(feature['geometry'])
                geom = GEOSGeometry(geom_str)
                # validate boundary_type
                boundary_type = None
                is_valid_boundary_type_value = (
                    check_valid_value(feature, layer_file.boundary_type)
                )
                if not is_valid_boundary_type_value:
                    error_found = True
                    layer_error[ErrorType.BOUNDARY_TYPE_ERROR.value] = (
                        ERROR_CHECK
                    )
                    level_error_report[
                        ErrorType.BOUNDARY_TYPE_ERROR.value] += 1
                else:
                    boundary_type_value = (
                        get_feature_value(feature, layer_file.boundary_type)
                    )
                    boundary_type = BoundaryType.objects.filter(
                        value=boundary_type_value,
                        dataset=dataset
                    ).first()
                    if not boundary_type:
                        error_found = True
                        layer_error[ErrorType.BOUNDARY_TYPE_ERROR.value] = (
                            ERROR_CHECK
                        )
                        level_error_report[
                            ErrorType.BOUNDARY_TYPE_ERROR.value] += 1
                    else:
                        boundary_type = boundary_type.type

                # check privacy level in feature layer file
                geo_privacy_level = dataset.max_privacy_level
                is_valid_privacy_level = True
                if layer_file.privacy_level:
                    geo_privacy_level = int(layer_file.privacy_level)
                elif layer_file.privacy_level_field:
                    # check for valid value of privacy level
                    is_valid_privacy_level = (
                        check_valid_value(feature,
                                          layer_file.privacy_level_field)
                    )
                    if is_valid_privacy_level:
                        privacy_level_value = (
                            get_feature_value(feature,
                                              layer_file.privacy_level_field)
                        )
                        try:
                            geo_privacy_level = int(privacy_level_value)
                        except ValueError:
                            is_valid_privacy_level = False
                    layer_error[ErrorType.PRIVACY_LEVEL_ERROR.value] = (
                        ERROR_CHECK if not is_valid_privacy_level else ''
                    )
                    if layer_error[ErrorType.PRIVACY_LEVEL_ERROR.value]:
                        error_found = True
                        level_error_report[
                            ErrorType.PRIVACY_LEVEL_ERROR.value
                        ] += 1

                # validate max privacy level in dataset
                is_allowed_privacy_level = True
                if not is_valid_privacy_level:
                    is_allowed_privacy_level = False
                else:
                    is_allowed_privacy_level = (
                        geo_privacy_level <= dataset.max_privacy_level
                    )
                layer_error[ErrorType.INVALID_PRIVACY_LEVEL.value] = (
                    ERROR_CHECK if not is_allowed_privacy_level else ''
                )
                if layer_error[ErrorType.INVALID_PRIVACY_LEVEL.value]:
                    error_found = True
                    level_error_report[
                        ErrorType.INVALID_PRIVACY_LEVEL.value
                    ] += 1

                if is_valid_privacy_level and is_allowed_privacy_level:
                    # check against min privacy level in dataset
                    if geo_privacy_level < dataset.min_privacy_level:
                        # upgrade to min_privacy_level
                        # TODO: need to show/flag this to FE
                        geo_privacy_level = dataset.min_privacy_level

                if error_found:
                    validation_summaries.append(layer_error)
                # if it's invalid boundary_type,
                # then no need to create the entity
                if not boundary_type:
                    continue
                start_date = (
                    entity_upload.upload_session.started_at if
                    not entity_upload.upload_session.is_historical_upload else
                    entity_upload.upload_session.historical_start_date
                )
                end_date = (
                    entity_upload.upload_session.historical_end_date if
                    entity_upload.upload_session.is_historical_upload else
                    None
                )
                geo, updated = GeographicalEntity.objects.update_or_create(
                    parent=None,
                    uuid=uuid.uuid4(),
                    revision_number=revision,
                    level=level,
                    defaults={
                        'layer_file': layer_file,
                        'dataset': dataset,
                        'start_date': start_date,
                        'end_date': end_date,
                        'type': boundary_type,
                        'label': internal_code,
                        'internal_code': internal_code,
                        'geometry': geom,
                        'is_approved': None,
                        'is_validated': False,
                        'is_latest': False,
                        'ancestor': None,
                        'admin_level_name': None,
                        'privacy_level': geo_privacy_level
                    }
                )
                # update simplify geom
                geo.do_simplification()
                # add extra id fields
                for id_field in layer_file.id_fields:
                    id_field_value = (
                        get_feature_value(feature, id_field['field'])
                    )
                    try:
                        EntityId.objects.create(
                            code_id=id_field['idType']['id'],
                            value=id_field_value,
                            default=False,
                            geographical_entity=geo
                        )
                    except IntegrityError:
                        pass
            error_summaries.append(level_error_report)

    if len(validation_summaries) > 0:
        entity_upload.status = ERROR
        entity_upload.summaries = error_summaries
        # Save error report to csv
        try:
            keys = validation_summaries[0].keys()
            csv_buffer = StringIO()
            csv_writer = csv.DictWriter(csv_buffer, keys)
            csv_writer.writeheader()
            csv_writer.writerows(validation_summaries)

            csv_file = ContentFile(csv_buffer.getvalue().encode('utf-8'))
            entity_upload.error_report.save(
                f'error-report-{entity_upload.id}.csv',
                csv_file
            )
        except Exception as e:
            logger.error(e)
    else:
        entity_upload.status = VALID

    entity_upload.save()

    # note: error/invalid geometries will be removed
    # only when upload is deleted
    if entity_upload.status == VALID:
        # generate unique_code_version for entity upload
        upload_session = entity_upload.upload_session
        revision_start_date = (
            upload_session.started_at if
            not upload_session.is_historical_upload else
            upload_session.historical_start_date
        )
        version = boundary_lines_upload_unique_code_version(
            dataset,
            revision_start_date
        )
        logger.info(f'Generating upload unique_code_version {version}')
        entity_upload.unique_code_version = version
        entity_upload.save()
        # generate unique code
        entities = GeographicalEntity.objects.filter(
            layer_file__in=layer_files
        ).order_by('id').iterator(chunk_size=1)
        for entity in entities:
            if not entity.unique_code:
                generate_unique_code(entity)

            if not entity.unique_code_version:
                entity.unique_code_version = entity_upload.unique_code_version
                entity.save()

    return entity_upload.status == VALID


def is_validation_result_importable(
        entity_upload: EntityUploadStatus, user) -> Tuple[bool, bool]:
    """
    Return whether the validation result can still be imported
    """
    is_warning = False
    is_importable = entity_upload.status == VALID
    if not is_importable and entity_upload.summaries:
        # check whether there is only overlaps error
        error_summaries = entity_upload.summaries
        allowable_errors = 0
        blocking_errors = 0
        superadmin_bypass_errors = 0
        superadmin_blocking_errors = 0
        for error_summary in error_summaries:
            for error_type in ErrorType:
                if error_type.value not in error_summary:
                    continue
                if error_type in ALLOWABLE_ERROR_TYPES:
                    allowable_errors += error_summary[error_type.value]
                else:
                    blocking_errors += error_summary[error_type.value]
                if error_type in SUPERADMIN_BYPASS_ERROR:
                    superadmin_bypass_errors += (
                        error_summary[error_type.value]
                    )
                else:
                    superadmin_blocking_errors += (
                        error_summary[error_type.value]
                    )
        if allowable_errors > 0 and blocking_errors == 0:
            is_importable = True
            is_warning = True
        # check if superadmin user:
        if user and user.is_superuser:
            if (
                superadmin_bypass_errors > 0 and
                superadmin_blocking_errors == 0
            ):
                is_importable = True
    return is_importable, is_warning


def reset_qc_validation(upload_session: LayerUploadSession):
    """
    Return:
     is_importable: whether the validation result can still be imported
     is_warning: whether the errors are considered as non-blocking error
    """
    layer_files = LayerFile.objects.filter(
        layer_upload_session=upload_session
    )
    GeographicalEntity.objects.filter(
        layer_file__in=layer_files
    ).delete()
    uploads = EntityUploadStatus.objects.filter(
        upload_session=upload_session
    )
    for upload in uploads:
        if upload.task_id:
            app.control.revoke(
                upload.task_id,
                terminate=True,
                signal='SIGKILL'
            )
        upload.status = ''
        upload.logs = ''
        upload.summaries = None
        upload.error_report = None
        upload.task_id = ''
        upload.save()


def boundary_lines_upload_unique_code_version(dataset: Dataset,
                                              start_date) -> float:
    next_entity = GeographicalEntity.objects.filter(
        dataset=dataset,
        start_date__gt=start_date,
        is_approved=True
    ).order_by('start_date').first()
    previous_entity = GeographicalEntity.objects.filter(
        dataset=dataset,
        start_date__lt=start_date,
        is_approved=True
    ).order_by('start_date').last()
    current_version = 1
    # Entity added before the first entity
    # e.g. first entity = 1, current version = 0.5
    if not previous_entity and next_entity:
        if next_entity.unique_code_version:
            current_version = next_entity.unique_code_version / 2

    # Entity added after the last entity
    # e.g. last entity version => 3, current version => 3 + 1 = 4
    if previous_entity and not next_entity:
        if previous_entity.unique_code_version:
            current_version = previous_entity.unique_code_version + 1

    # Entity added between entities
    if previous_entity and next_entity:
        if (
            previous_entity.unique_code_version and
            next_entity.unique_code_version
        ):
            current_version = (
                  previous_entity.unique_code_version +
                  next_entity.unique_code_version
            ) / 2
    return current_version


def get_error_types():
    error_types = []
    nonblocking_types = []
    for error_type in ErrorType:
        if error_type in ALLOWABLE_ERROR_TYPES:
            nonblocking_types.append(error_type.value)
        else:
            error_types.append(error_type.value)
    return {
        'error': error_types,
        'warning': nonblocking_types
    }
