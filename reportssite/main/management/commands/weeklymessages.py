import datetime
from threading import Thread
from django.utils import timezone
from django.core.management.base import BaseCommand

from non_repairability_act.models import NonRepairabilityAct, ActStatusHistory, ActStatus
from mail.views import mail_new_acts


class Command(BaseCommand):
    """ Send NRP acts for wwek. """
    
    help = "NRP acts weekly messages."

    def handle(self, *args, **options):
        send_date = timezone.now() - datetime.timedelta(days=7)
        history = ActStatusHistory.objects.filter(
            status=ActStatus.SEND,
            created_at__gt=send_date
            ).values('act__pk')
        acts = NonRepairabilityAct.objects.filter(pk__in=history).values(
            'pk',
            'product__title',
            'model_description',
            'serial_number',
            'center__title',
            'center__city'
        )
        if acts:
            Thread(
                target=mail_new_acts, args=(
                    send_date,
                    acts,
                    )
                ).start()
        self.stdout.write(
                self.style.SUCCESS('NRP acts weekly send.')
            )
    