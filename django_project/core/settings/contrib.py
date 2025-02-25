# coding=utf-8
"""Settings for 3rd party."""
from .base import *  # noqa
from corsheaders.defaults import default_headers

# Extra installed apps
INSTALLED_APPS = INSTALLED_APPS + (
    'rest_framework',
    'knox',
    'rest_framework_gis',
    'rest_framework.authtoken',
    'drf_yasg',
    'webpack_loader',
    'corsheaders',
    'guardian',
    'django_cleanup.apps.CleanupConfig',
    'django_celery_beat',
    'django_celery_results',
    'tinymce',
    'taggit',
    'captcha'
)
WEBPACK_LOADER = {
    'DEFAULT': {
        'BUNDLE_DIR_NAME': 'dashboard/',  # must end with slash
        'STATS_FILE': absolute_path('dashboard', 'webpack-stats.prod.json'),
        'POLL_INTERVAL': 0.1,
        'TIMEOUT': None,
        'IGNORE': [r'.+\.hot-update.js', r'.+\.map'],
        'LOADER_CLASS': 'webpack_loader.loader.WebpackLoader',
    }
}
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'georepo.auth.BearerAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_VERSIONING_CLASS': (
        'rest_framework.versioning.NamespaceVersioning'
    ),
    'EXCEPTION_HANDLER': 'georepo.utils.custom_exception_handler'
}
CORS_ORIGIN_ALLOW_ALL = True
CORS_ALLOW_HEADERS = (
    *default_headers,
    "GeoRepo-User-Key",
)
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',  # default
    'guardian.backends.ObjectPermissionBackend'
]
DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'
CELERY_RESULT_BACKEND = 'django-db'
CELERY_RESULT_EXTENDED = True
# set to 500mb
CELERY_WORKER_MAX_MEMORY_PER_CHILD = 300000
#knox setting
REST_KNOX = {
  'SECURE_HASH_ALGORITHM': 'cryptography.hazmat.primitives.hashes.SHA512',
  'AUTH_TOKEN_CHARACTER_LENGTH': 64,
  'TOKEN_TTL': None,
  'USER_SERIALIZER': 'knox.serializers.UserSerializer',
  'TOKEN_LIMIT_PER_USER': 1,
  'AUTO_REFRESH': False,
}
