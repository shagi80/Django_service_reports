from django.apps import AppConfig


class NonRepairabilityActConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'non_repairability_act'
    verbose_name = 'Акты неремотопригодносты'

    def ready(self):
        import non_repairability_act.signals

        return super().ready()
