from django.apps import AppConfig


class DocProcessingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'doc_processing'

    def ready(self):
        from . import data_initializer
        data_initializer.build_data_once()
