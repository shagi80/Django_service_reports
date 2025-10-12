from django.apps import AppConfig


class ReportsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'reports'
    verbose_name = 'Отчеты'

    def ready(self):
        from .ml_model.ml_model import MLModelLoader
        MLModelLoader.get_classifier()
