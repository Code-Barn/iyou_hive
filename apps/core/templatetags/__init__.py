from django.apps import AppConfig

class CoreAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'
    label = 'core'

    def ready(self):
        # Register template tags
        from django.template.utils import get_app_package
        get_app_package(__package__)
