import math
import os.path
import shutil
import tempfile
import zipfile

from django import forms
from django.conf import settings
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import (
    UserChangeForm, ReadOnlyPasswordHashField
)
from django.http import HttpResponse
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from guardian.admin import GuardedModelAdmin
from rest_framework.authtoken.models import Token

from core.settings.utils import absolute_path
from georepo.forms import (
    AzureAdminUserCreationForm,
    AzureAdminUserChangeForm,
    DatasetAdminCreationForm,
    DatasetAdminChangeForm
)
from georepo.models import (
    GeographicalEntity,
    Language,
    EntityType,
    EntityName,
    Dataset,
    CodeCL,
    EntityCode,
    LayerStyle,
    DatasetTilingConfig,
    DatasetGroup,
    DatasetView,
    Module,
    IdType,
    AdminLevelTilingConfig,
    BoundaryType,
    TaggedRecord,
    TagWithDescription,
    DatasetViewTilingConfig,
    ViewAdminLevelTilingConfig,
    DatasetViewResource,
    GeorepoRole,
    UserAccessRequest
)
from georepo.utils.admin import (
    # get_deleted_objects,
    delete_selected
)
from georepo.utils.dataset_view import (
    get_view_tiling_status
)

User = get_user_model()


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def get_folder_size(directory_path):
    if not os.path.exists(directory_path):
        return '0'
    folder_size = 0
    # get size
    for path, dirs, files in os.walk(directory_path):
        for f in files:
            fp = os.path.join(path, f)
            folder_size += os.stat(fp).st_size
    return convert_size(folder_size)


def move_directory(old_directory, new_directory):
    if not os.path.exists(old_directory):
        return
    if os.path.exists(new_directory):
        return
    shutil.move(
        old_directory,
        new_directory
    )


class GeographicalEntityAdmin(admin.ModelAdmin):
    actions = []
    list_display = (
        'label', 'unique_code', 'level', 'type',
        'revision_number', 'dataset', 'is_latest', 'is_approved'
    )
    list_filter = (
        'level', 'type', 'revision_number', 'dataset',
        'is_latest', 'is_approved'
    )
    search_fields = (
        'label',
        'unique_code'
    )
    raw_id_fields = (
        'parent',
        'ancestor'
    )

    def get_queryset(self, request):
        return GeographicalEntity.objects.filter(id__gte=0)


def populate_default_tile_config(modeladmin, request, queryset):
    from georepo.utils.tile_configs import populate_tile_configs
    for dataset in queryset:
        populate_tile_configs(dataset.id)
    modeladmin.message_user(
        request,
        'Dataset tile configs has been successfully generated!',
        messages.SUCCESS
    )


def populate_default_admin_level_names(modeladmin, request, queryset):
    from dashboard.tools.admin_level_names import \
        populate_default_dataset_admin_level_names
    for dataset in queryset:
        populate_default_dataset_admin_level_names(dataset)
    modeladmin.message_user(
        request,
        'Dataset admin level names has been successfully generated!',
        messages.SUCCESS
    )


def generate_simplified_geometry(modeladmin, request, queryset):
    from georepo.tasks.simplify_geometry import simplify_geometry_in_dataset
    from celery.result import AsyncResult
    from core.celery import app
    for dataset in queryset:
        if dataset.simplification_task_id:
            res = AsyncResult(dataset.simplification_task_id)
            if not res.ready():
                app.control.revoke(
                    dataset.simplification_task_id,
                    terminate=True
                )
        task = simplify_geometry_in_dataset.delay(dataset.id)
        dataset.simplification_task_id = task.id
        dataset.simplification_progress = 'Started'
        dataset.save(
            update_fields=['simplification_task_id',
                           'simplification_progress']
        )
    modeladmin.message_user(
        request,
        'Dataset entity simplification will be run in background!',
        messages.SUCCESS
    )


def do_dataset_patch(modeladmin, request, queryset):
    from georepo.tasks.dataset_patch import dataset_patch
    for dataset in queryset:
        dataset_patch.delay(dataset.id)
    modeladmin.message_user(
        request,
        'Dataset patch will be run in background!',
        messages.SUCCESS
    )


@admin.action(description='Generate default views (not adm0)')
def generate_default_views(modeladmin, request, queryset):
    from georepo.utils.dataset_view import (
        generate_default_view_dataset_latest,
        generate_default_view_dataset_all_versions
    )
    for dataset in queryset:
        generate_default_view_dataset_latest(dataset)
        generate_default_view_dataset_all_versions(dataset)


@admin.action(description='Refresh dynamic views')
def refresh_dynamic_views(modeladmin, request, queryset):
    from georepo.utils.dataset_view import trigger_generate_dynamic_views
    for dataset in queryset:
        trigger_generate_dynamic_views(dataset)


@admin.action(description='Generate arcgis config')
def generate_arcgis_config_action(modeladmin, request, queryset):
    from georepo.utils.arcgis import generate_arcgis_config
    # check if user has API key
    if not Token.objects.filter(user=request.user).exists():
        modeladmin.message_user(
            request,
            'Please generate API Key for your user account!',
            messages.ERROR
        )
        return
    for dataset in queryset:
        generate_arcgis_config(request.user, dataset, None)


@admin.action(description='Clear cache')
def clear_cache(modeladmin, request, queryset):
    from django.core.cache import cache
    cache.clear()


@admin.action(description='Generate jmeter script')
def generate_jmeter_script(modeladmin, request, queryset):
    from georepo.utils.jmeter import generate_jmeter_scripts
    csv_data = generate_jmeter_scripts()
    with tempfile.SpooledTemporaryFile() as tmp_file:
        with zipfile.ZipFile(
                tmp_file, 'w', zipfile.ZIP_DEFLATED) as archive:
            for csv_name, csv_value in csv_data.items():
                archive.writestr(
                    csv_name,
                    csv_value)
                template_name = csv_name.split('.')[0]
                template_path = absolute_path(
                    'georepo',
                    'utils',
                    'jmeter_templates',
                    f'{template_name}.jmx'
                )
                archive.write(template_path, arcname=f'{template_name}.jmx')

        tmp_file.seek(0)
        response = HttpResponse(
            tmp_file.read(), content_type='application/x-zip-compressed'
        )
        response['Content-Disposition'] = (
            'attachment; filename="jmeter.zip"'
        )
        return response


@admin.action(description='Add to public groups')
def add_to_public_groups(modeladmin, request, queryset):
    from georepo.utils.permission import grant_dataset_to_public_groups
    for dataset in queryset:
        grant_dataset_to_public_groups(dataset)


@admin.action(description='Generate Concept UCode')
def generate_dataset_concept_ucode(modeladmin, request, queryset):
    from georepo.tasks.dataset_patch import generate_concept_ucode
    for dataset in queryset:
        generate_concept_ucode.delay(dataset.id)


@admin.action(description='Patch entity names')
def patch_entity_names(modeladmin, request, queryset):
    from dashboard.tasks import fix_entity_name_encoding
    for dataset in queryset:
        fix_entity_name_encoding.delay(dataset.id)


class DatasetAdmin(GuardedModelAdmin):
    add_form_template = None
    form = DatasetAdminChangeForm
    add_form = DatasetAdminCreationForm
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('label', 'description', 'module', 'short_code',
                       'max_privacy_level', 'min_privacy_level',),
        }),
    )
    list_display = (
        'label', 'short_code', 'max_privacy_level', 'min_privacy_level',
        'uuid', 'arcgis_config')
    actions = [
        delete_selected,
        populate_default_tile_config, generate_simplified_geometry,
        do_dataset_patch, refresh_dynamic_views,
        populate_default_admin_level_names,
        generate_arcgis_config_action,
        clear_cache, generate_jmeter_script,
        generate_default_views, add_to_public_groups,
        generate_dataset_concept_ucode, patch_entity_names]

    def get_form(self, request, obj=None, **kwargs):
        """
        Use creation form during Dataset creation
        """
        defaults = {}
        if obj is None:
            defaults['form'] = self.add_form
        defaults.update(kwargs)
        form = super().get_form(request, obj, **defaults)
        form.user = request.user
        return form

    def arcgis_config(self, obj: Dataset):
        from georepo.utils.arcgis import (
            ARCGIS_BASE_CONFIG_PATH
        )
        config_path = (
            f'{obj.label.lower().replace(" ", "_")}'
            '/VectorTileServer/resources/styles/root.json'
        )
        arcgis_config_full_path = os.path.join(
            ARCGIS_BASE_CONFIG_PATH,
            config_path,
        )
        if arcgis_config_full_path:
            return format_html(
                f'<a href="{settings.LAYER_TILES_BASE_URL}'
                f'/arcgis/rest/services/{config_path}" target="_blank">'
                'Arcgis Config</a>'
            )
        else:
            return '-'

    # Uncomment this function when we want to simplify
    # the delete confirmation page
    # def get_deleted_objects(self, objs, request):
    #     """
    #     Hook for customizing the delete process for the delete view and the
    #     "delete selected" action.
    #     """
    #     return get_deleted_objects(objs, request, self.admin_site, True)


class LayerStyleAdmin(admin.ModelAdmin):
    list_display = ('label', 'dataset', 'level', 'type')


class AdminLevelTilingConfigInline(admin.TabularInline):
    model = AdminLevelTilingConfig
    extra = 0


class DatasetTilingConfigAdmin(admin.ModelAdmin):
    list_display = (
        'dataset', 'zoom_level'
    )
    inlines = [
        AdminLevelTilingConfigInline,
    ]


class ViewAdminLevelTilingConfigInline(admin.TabularInline):
    model = ViewAdminLevelTilingConfig
    extra = 0


class DatasetViewTilingConfigAdmin(admin.ModelAdmin):
    list_display = (
        'dataset_view', 'zoom_level'
    )
    inlines = [
        ViewAdminLevelTilingConfigInline,
    ]


class IdTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_by', 'created_at')


@admin.action(description='Generate exported data')
def generate_view_exported_data(modeladmin, request, queryset):
    from dashboard.tasks import generate_view_export_data
    from celery.result import AsyncResult
    from core.celery import app
    for dataset_view in queryset:
        if dataset_view.task_id:
            # find if there is running task and stop it
            res = AsyncResult(dataset_view.task_id)
            if not res.ready():
                app.control.revoke(dataset_view.task_id, terminate=True)
        task = generate_view_export_data.delay(dataset_view.id)
        dataset_view.task_id = task.id
        dataset_view.save()


@admin.action(description='Create SQL View')
def create_sql_view_action(modeladmin, request, queryset):
    from georepo.utils import create_sql_view
    for dataset_view in queryset:
        create_sql_view(dataset_view)


@admin.action(description='Generate vector tiles')
def generate_view_vector_tiles(modeladmin, request, queryset):
    from georepo.utils.dataset_view import (
        trigger_generate_vector_tile_for_view
    )
    for dataset_view in queryset:
        trigger_generate_vector_tile_for_view(dataset_view,
                                              export_data=False)


def download_view_size_action(modeladmin, request, queryset):
    import csv
    # Create the HttpResponse object with the appropriate CSV header.
    response = HttpResponse(
        content_type='text/csv',
        headers={
            'Content-Disposition': 'attachment; filename="storage_usage.csv"'
        },
    )

    writer = csv.writer(response)
    writer.writerow(['View', 'Vector Tiles', 'Shapefile', 'Geojson'])
    for dataset_view in queryset:
        tile_path = os.path.join(
            settings.LAYER_TILES_PATH,
            str(dataset_view.uuid)
        )
        vector_tile_size = get_folder_size(tile_path)
        geojson_path = os.path.join(
            settings.GEOJSON_FOLDER_OUTPUT,
            str(dataset_view.uuid)
        )
        geojson_size = get_folder_size(geojson_path)
        shapefile_path = os.path.join(
            settings.SHAPEFILE_FOLDER_OUTPUT,
            str(dataset_view.uuid)
        )
        shapefile_size = get_folder_size(shapefile_path)
        writer.writerow([
            dataset_view.name,
            vector_tile_size,
            geojson_size,
            shapefile_size
        ])
    return response


@admin.action(description='Fix Privacy Level')
def fix_view_privacy_level(modeladmin, request, queryset):
    from georepo.utils.dataset_view import init_view_privacy_level
    for dataset_view in queryset:
        init_view_privacy_level(dataset_view)


def view_generate_simplified_geometry(modeladmin, request, queryset):
    from georepo.tasks.simplify_geometry import simplify_geometry_in_view
    from celery.result import AsyncResult
    from core.celery import app
    for dataset_view in queryset:
        if dataset_view.simplification_task_id:
            res = AsyncResult(dataset_view.simplification_task_id)
            if not res.ready():
                app.control.revoke(
                    dataset_view.simplification_task_id,
                    terminate=True
                )
        task = simplify_geometry_in_view.delay(dataset_view.id)
        dataset_view.simplification_task_id = task.id
        dataset_view.simplification_progress = 'Started'
        dataset_view.save(
            update_fields=['simplification_task_id',
                           'simplification_progress']
        )
    modeladmin.message_user(
        request,
        'Dataset entity simplification will be run in background!',
        messages.SUCCESS
    )


@admin.action(description='Fix Entity Count in View')
def fix_view_entity_count(modeladmin, request, queryset):
    from georepo.utils.dataset_view import get_entities_count_in_view
    for dataset_view in queryset:
        view_resources = DatasetViewResource.objects.filter(
            dataset_view=dataset_view
        )
        for view_resource in view_resources:
            view_resource.entity_count = (
                get_entities_count_in_view(
                    dataset_view, view_resource.privacy_level
                )
            )
            view_resource.save(update_fields=['entity_count'])


class DatasetViewAdmin(GuardedModelAdmin):
    list_display = (
        'name', 'dataset', 'is_static', 'min_privacy_level',
        'max_privacy_level', 'tiling_status', 'uuid')
    search_fields = ['name', 'dataset__label', 'uuid']
    actions = [generate_view_vector_tiles, create_sql_view_action,
               generate_view_exported_data,
               fix_view_privacy_level,
               fix_view_entity_count,
               view_generate_simplified_geometry]

    def tiling_status(self, obj: DatasetView):
        status, _ = get_view_tiling_status(
            DatasetViewResource.objects.filter(
                dataset_view=obj
            )
        )
        return status


class LanguageAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'native_name', 'order')
    search_fields = ('name', 'code')
    change_list_template = 'language_change_list.html'


class BoundaryTypeAdmin(admin.ModelAdmin):
    list_display = ('type', 'value', 'dataset')


class EntityNameAdmin(admin.ModelAdmin):
    raw_id_fields = ('geographical_entity', 'language')
    list_display = ('name', 'geographical_entity', 'language')


class TaggedRecordInline(admin.StackedInline):
    model = TaggedRecord


class TagAdmin(admin.ModelAdmin):
    model = TagWithDescription
    inlines = [TaggedRecordInline]
    list_display = ["name", "slug"]
    ordering = ["name", "slug"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ["name"]}


@admin.action(description='Regenerate Vector Tiles')
def regenerate_resource_vector_tiles(modeladmin, request, queryset):
    from celery.result import AsyncResult
    from core.celery import app
    from dashboard.tasks import (
        generate_view_vector_tiles_task
    )
    for view_resource in queryset:
        if view_resource.vector_tiles_task_id:
            res = AsyncResult(view_resource.vector_tiles_task_id)
            if not res.ready():
                # find if there is running task and stop it
                app.control.revoke(view_resource.vector_tiles_task_id,
                                   terminate=True)
        view_resource.status = DatasetView.DatasetViewStatus.PENDING
        view_resource.vector_tiles_progress = 0
        view_resource.save()
        task = generate_view_vector_tiles_task.apply_async(
            (view_resource.id, True, True),
            queue='tegola'
        )
        view_resource.vector_tiles_task_id = task.id
        view_resource.save(update_fields=['vector_tiles_task_id'])


@admin.action(description='Resume Vector Tiles Generation')
def resume_vector_tiles_generation(modeladmin, request, queryset):
    from celery.result import AsyncResult
    from core.celery import app
    from dashboard.tasks import (
        generate_view_vector_tiles_task
    )
    for view_resource in queryset:
        if view_resource.vector_tiles_task_id:
            res = AsyncResult(view_resource.vector_tiles_task_id)
            if not res.ready():
                # find if there is running task and stop it
                app.control.revoke(view_resource.vector_tiles_task_id,
                                   terminate=True)
        view_resource.status = DatasetView.DatasetViewStatus.PENDING
        view_resource.vector_tiles_progress = 0
        view_resource.save()
        task = generate_view_vector_tiles_task.apply_async(
            (view_resource.id, True, False),
            queue='tegola'
        )
        view_resource.vector_tiles_task_id = task.id
        view_resource.save(update_fields=['vector_tiles_task_id'])


@admin.action(description='Calculate Vector Tiles Size')
def calculate_vector_tile_size(modeladmin, request, queryset):
    from georepo.utils.vector_tile import calculate_vector_tiles_size
    for view_resource in queryset:
        calculate_vector_tiles_size(view_resource)


@admin.action(description='Cleanup tegola config files')
def cleanup_tegola_configs(modeladmin, request, queryset):
    from georepo.utils.vector_tile import clean_tegola_config_files
    for view_resource in queryset:
        clean_tegola_config_files(view_resource)


@admin.action(description='Fix Entity Count in Resource')
def fix_entity_count_in_resource(modeladmin, request, queryset):
    from georepo.utils.dataset_view import get_entities_count_in_view
    for view_resource in queryset:
        view_resource.entity_count = (
            get_entities_count_in_view(
                view_resource.dataset_view,
                view_resource.privacy_level
            )
        )
        view_resource.save(update_fields=['entity_count'])


class DatasetViewResourceAdmin(admin.ModelAdmin):
    search_fields = ['dataset_view__name', 'uuid']
    actions = [
        calculate_vector_tile_size,
        regenerate_resource_vector_tiles,
        resume_vector_tiles_generation,
        cleanup_tegola_configs,
        fix_entity_count_in_resource
    ]

    def get_list_display(self, request):
        def layer_preview(obj: DatasetViewResource):
            # check if user has API key
            if not settings.USE_AZURE:
                if not Token.objects.filter(user=request.user).exists():
                    return 'Require User API Key!'
            if obj.vector_tiles_exist:
                return format_html(
                    '<a href="/layer-test/'
                    '?dataset_view_resource={}">Layer Preview</a>'
                    ''.format(
                        obj.id))
            return '-'

        def size(obj: DatasetViewResource):
            return convert_size(obj.vector_tiles_size)
        return ('dataset_view', 'privacy_level', 'entity_count', 'uuid',
                'status', 'vector_tiles_progress', size,
                layer_preview)


class ModuleAdmin(GuardedModelAdmin):
    list_display = (
        'name', 'uuid', 'created_at')


class UserAccessRequestAdmin(admin.ModelAdmin):
    list_display = ('requester_email', 'requester_first_name', 'type',
                    'status', 'submitted_on')
    search_fields = ['requester_first_name', 'requester_email',
                     'type', 'status']


admin.site.register(GeographicalEntity, GeographicalEntityAdmin)
admin.site.register(Language, LanguageAdmin)
admin.site.register(EntityType)
admin.site.register(EntityName, EntityNameAdmin)
admin.site.register(CodeCL)
admin.site.register(EntityCode)
admin.site.register(Dataset, DatasetAdmin)
admin.site.register(LayerStyle, LayerStyleAdmin)
admin.site.register(DatasetTilingConfig, DatasetTilingConfigAdmin)
admin.site.register(DatasetViewTilingConfig, DatasetViewTilingConfigAdmin)
admin.site.register(Module, ModuleAdmin)
admin.site.register(DatasetGroup)
admin.site.register(DatasetView, DatasetViewAdmin)
admin.site.register(IdType, IdTypeAdmin)
admin.site.register(BoundaryType, BoundaryTypeAdmin)
admin.site.register(TagWithDescription, TagAdmin)
admin.site.register(DatasetViewResource, DatasetViewResourceAdmin)
admin.site.register(UserAccessRequest, UserAccessRequestAdmin)


# Define inline formset
class RoleInlineFormSet(forms.BaseInlineFormSet):
    def save_new(self, form, commit=True):
        if self.cleaned_data:
            user = self.cleaned_data[0].get('user')
            if user:
                # check if existing has been created
                role = GeorepoRole.objects.filter(
                    user=user
                ).first()
                if role:
                    # update the role with value
                    role.type = self.cleaned_data[0].get('type')
                    role.save()
                    return role
        return super(RoleInlineFormSet, self).save_new(form, commit=commit)


# Define an inline admin descriptor for Role model
# which acts a bit like a singleton
class RoleInline(admin.StackedInline):
    model = GeorepoRole
    can_delete = False
    verbose_name_plural = 'profiles'
    formset = RoleInlineFormSet


class CustomUserChangeForm(UserChangeForm):
    """Custom user change form."""

    username = forms.CharField(
        help_text=_(
            'Required. 150 characters or fewer. '
            'Letters, digits and @/./+/-/_/# only.'
        ),
    )

    password = ReadOnlyPasswordHashField(
        label=_("Password"),
        help_text=_(
            "Passwords are not stored in this site."
        ),
    )


class CustomUserCreationForm(forms.ModelForm):
    """Custom user change form."""

    username = forms.CharField(
        help_text=_(
            'Required. 150 characters or fewer. '
            'Letters, digits and @/./+/-/_/# only.'
        ),
    )

    class Meta:
        model = User
        fields = ("username",)

    def __init__(self, *args, **kwargs):
        super(CustomUserCreationForm, self).__init__(*args, **kwargs)

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_unusable_password()
        if commit:
            user.save()
        return user


# USER ADMIN BASED ON USING AZURE OR NOT
admin.site.unregister(User)
if settings.USE_AZURE:
    class UserProfileAdmin(BaseUserAdmin):
        """User profile admin."""

        add_form_template = None
        form = AzureAdminUserChangeForm
        add_form = AzureAdminUserCreationForm
        inlines = (RoleInline,)
        list_display = (
            'username', 'email', 'first_name', 'last_name', 'is_staff'
        )
        add_fieldsets = (
            (None, {
                'classes': ('wide',),
                'fields': ('email',),
            }),
        )
        fieldsets = (
            (None, {'fields': ('email',)}),
            (_('Personal info'),
             {'fields': ('first_name', 'last_name')}),
            (_('Permissions'), {
                'fields': (
                    'is_active', 'is_staff', 'is_superuser', 'groups',
                    'user_permissions'
                ),
            }),
            (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
        )


    admin.site.register(User, UserProfileAdmin)
else:
    class UserProfileAdmin(BaseUserAdmin):
        """User profile admin."""

        inlines = (RoleInline,)


    admin.site.register(User, UserProfileAdmin)


# Re-register UserAdmin
# admin.site.register(User, UserProfileAdmin)
