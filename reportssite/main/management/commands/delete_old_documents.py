import os
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand
from django.utils import timezone

from non_repairability_act.models import ActDocumnent
from upload.models import RecordDocumnent, ReportDocumnent


class Command(BaseCommand):
    help = 'Deletes document files older than N months and replaces them with a placeholder'

    def handle(self, *args, **options):
        # === SETTINGS ===
        MONTHS_THRESHOLD = 24  # File age in months
        PLACEHOLDER_PATH = 'main/default_doc.jpg'  # Path inside MEDIA_ROOT

        full_placeholder_path = os.path.join(settings.MEDIA_ROOT, PLACEHOLDER_PATH)
        if not os.path.exists(full_placeholder_path):
            self.stderr.write(self.style.ERROR(f'Placeholder file not found: {full_placeholder_path}'))
            return

        cutoff_date = timezone.now().date() - timedelta(days=MONTHS_THRESHOLD * 30.4375)
        self.stdout.write(f'Searching for documents older than {cutoff_date}...')

        models_to_clean = [ActDocumnent, ReportDocumnent, RecordDocumnent]
        total_cleaned = 0

        for model in models_to_clean:
            cleaned = self._process_model(model, cutoff_date, PLACEHOLDER_PATH)
            total_cleaned += cleaned
            self.stdout.write(f'{model.__name__}: cleaned - {cleaned}')

        self.stdout.write(self.style.SUCCESS(f'Done! Total files cleaned: {total_cleaned}'))

    def _process_model(self, model, cutoff_date, placeholder_path):
        queryset = model.objects.filter(date__lt=cutoff_date).exclude(file=placeholder_path)
        count = 0

        for obj in queryset.iterator():
            if not obj.file:
                continue

            try:
                if obj.file.storage.exists(obj.file.name):
                    obj.file.storage.delete(obj.file.name)
            except Exception as e:
                self.stderr.write(f'Error deleting {obj.file.name} (ID {obj.pk}): {e}')
                continue

            obj.file.name = placeholder_path
            obj.save(update_fields=['file'])
            count += 1

        return count
