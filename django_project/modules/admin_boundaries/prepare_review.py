import logging
from dashboard.models.entity_upload import (
    EntityUploadStatus, REVIEWING
)
from modules.admin_boundaries.admin_boundary_matching import (
    AdminBoundaryMatching
)

logger = logging.getLogger(__name__)


def ready_to_review(entity_uploads):
    """Update entity_uploads to REVIEWING."""
    entity_uploads.update(
        status=REVIEWING,
        progress='Pending Boundary Matching'
    )


def prepare_review(entity_upload: EntityUploadStatus):
    """Run boundary matching."""
    logger.info('prepare for review of admin_boundaries')
    admin_boundary_matching = (
        AdminBoundaryMatching(entity_upload=entity_upload)
    )
    admin_boundary_matching.run()
