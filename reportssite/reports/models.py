from django.contrib.auth.models import User
from django.db import models
from django.db.models import Sum, Q
from django.urls import reverse
from main.my_validators import ChangeloggableMixin
from servicecentres.models import ServiceCenters
from main.business_logic import (
    REPORT_STATUS,
    STATUS_DRAFT,
    WORKTYPE,
    FACTORIES,
    MONTH_CHOICES,
)
from products.models import Codes, MainProducts, Models
from django.db.models.signals import (
    pre_save,
    post_save,
    pre_delete,
    post_delete,
)
from django.dispatch import receiver


class ClientType(models.TextChoices):
    ORGANIZATION = 'organization', 'организация'
    INDIVIDUAL = 'individual', 'физлицо'


def ReportDateValidation(self):
    return Reports.ojects.filter(report_date=self.report_date).exclude(
        pk=self.pk
    )


class Reports(ChangeloggableMixin, models.Model):
    service_center = models.ForeignKey(
        ServiceCenters,
        on_delete=models.CASCADE,
        verbose_name='Сервисный центр',
    )
    report_date = models.DateField(verbose_name='Отчетный период')
    note = models.TextField(blank=True, null=True, verbose_name='Примечание')
    user = models.ForeignKey(
        User,
        verbose_name='Автор отчета',
        on_delete=models.PROTECT,
        limit_choices_to={'is_staff': False},
    )
    status = models.CharField(
        choices=REPORT_STATUS,
        max_length=100,
        verbose_name='Статус',
        default=STATUS_DRAFT,
    )
    total_cost = models.FloatField(
        default=0, verbose_name='Общая сумма по отчету'
    )
    total_work = models.FloatField(
        default=0, verbose_name='Общая сумма за работы'
    )
    total_part = models.FloatField(
        default=0, verbose_name='Общая сумма за детали'
    )
    total_move = models.FloatField(
        default=0, verbose_name='Общая сумма за выезд'
    )
    records_count = models.IntegerField(
        default=0, verbose_name='Количестов ремонтов'
    )
    verified_count = models.IntegerField(
        default=0, verbose_name='Количестов принятых ремонтов'
    )
    have_fault = models.BooleanField(
        default=False, blank=True, verbose_name='Имеет ошибки'
    )
    pay_date = models.DateField(
        blank=True, null=True, verbose_name='Дата передачи в оплату'
    )
    send_date = models.DateField(
        blank=True, null=True, verbose_name='Дата отправки на проверку'
    )

    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        ordering = ['-report_date', 'service_center', 'status']

    def __str__(self):
        date = self.report_date
        return (f'{self.service_center.title} за'
                f'{MONTH_CHOICES[date.month-1][1]}{date.strftime(" %Y")} года')

    def get_report_month(self):
        return ' '.join(
            [
                MONTH_CHOICES[self.report_date.month - 1][1],
                self.report_date.strftime('%Y'),
            ]
        )

    def get_absolute_url(self):
        return reverse(
            'report_page',
            kwargs={
                'pk': self.pk,
            },
        )

    def get_report_documents(self):
        """формирование строки из номера акта и счета (при наличии)"""

        docs = self.reportdocumnent_set.filter(title__in=['act', 'invoice'])
        text = ''
        for doc in docs:
            text = (f'{text} {doc.get_title_display()} '
                    f'№{doc.number} от {str(doc.date)},')
        return text[:-1] if text else '...'


class ReportsRecords(ChangeloggableMixin, models.Model):
    product = models.ForeignKey(
        MainProducts, verbose_name='Тип продукции', on_delete=models.PROTECT
    )
    model = models.ForeignKey(
        Models,
        null=True,
        blank=True,
        verbose_name='Модель продукции',
        on_delete=models.PROTECT,
    )
    work_type = models.CharField(
        choices=WORKTYPE, max_length=50, verbose_name='Вид ремонта'
    )
    client_type = models.CharField(
        choices=ClientType.choices,
        max_length=50,
        null=True,
        blank=True,
        verbose_name='Тип клиента',
    )
    client = models.CharField(
        max_length=150, null=True, blank=True, verbose_name='Клиент'
    )
    client_phone = models.CharField(
        max_length=150, null=True, blank=True, verbose_name='Телефон клиента'
    )
    client_addr = models.CharField(
        max_length=250, null=True, blank=True, verbose_name='Адрес клиента'
    )
    client_email = models.EmailField(
        max_length=500, null=True, blank=True, verbose_name='E-mail клиента'
    )
    model_description = models.CharField(
        max_length=150, verbose_name='Модель продукции', blank=True
    )
    serial_number = models.CharField(
        max_length=30, verbose_name='Серийный номер'
    )
    buy_date = models.DateField(
        null=True, blank=True, verbose_name='Дата покупки'
    )
    start_date = models.DateField(verbose_name='Дата начала ремонта')
    end_date = models.DateField(
        null=True, blank=True, verbose_name='Дата окончания ремонта'
    )
    work_cost = models.FloatField(default=0, verbose_name='За работу')
    move_cost = models.FloatField(
        default=0, verbose_name='За выезд', blank=True
    )
    problem_description = models.TextField(verbose_name='Описание проблемы')
    work_description = models.TextField(
        verbose_name='Описание работ', blank=True
    )
    code = models.ForeignKey(
        Codes,
        verbose_name='Код неисправности',
        on_delete=models.PROTECT,
        limit_choices_to={'is_folder': False},
    )
    note = models.CharField(
        max_length=250, verbose_name='Примечание', blank=True
    )
    report = models.ForeignKey(
        Reports,
        verbose_name='Отчет',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
    )
    parts_cost = models.FloatField(
        default=0, verbose_name='За детали', blank=True
    )
    total_cost = models.FloatField(
        default=0, verbose_name='Всего за ремонт', blank=True
    )

    verified = models.BooleanField(default=False, verbose_name='Принят')
    factory = models.CharField(
        choices=FACTORIES,
        null=True,
        max_length=1,
        verbose_name='Завод-изготовитель',
        blank=True,
    )
    main_date = models.DateField(
        null=True, verbose_name='Дата производства', blank=True
    )
    shift = models.CharField(
        null=True, max_length=1, verbose_name='Рабочая смена', blank=True
    )
    errors = models.TextField(verbose_name='Ошибки', null=True, blank=True)
    remarks = models.TextField(verbose_name='Замечания', null=True, blank=True)
    have_general_errors = models.BooleanField(
        default=False, verbose_name='Требует внимания старшего менеджера'
    )
    verified_date = models.DateField(
        verbose_name='Дата приема записи', null=True, blank=True
    )
    order_parts = models.BooleanField(
        default=False, verbose_name='Запчасти заказаны'
    )
    # 20.01.2024. Заполнение на основании Акта НРП.
    parent_act = models.ForeignKey(
        'non_repairability_act.NonRepairabilityAct',
        null=True,
        blank=True,
        related_name='child_record',
        verbose_name='Акт-основание',
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = 'Ремонт'
        verbose_name_plural = 'Ремонты'
        ordering = [
            'report',
        ]

    def get_absolute_url(self):
        return reverse(
            'record_update_page',
            kwargs={
                'pk': self.pk,
            },
        )

    def __str__(self):
        return str(self.report) + ' ' + self.serial_number

    @property
    def status(self):
        if self.end_date:
            status = 'work_end'
        else:
            status = 'draft'
            parts = self.reportsparts_set.all()
            parts_order_count = parts.filter(order_date__isnull=False).count()
            parts_send_count = parts.filter(
                order_date__isnull=False, send_date__isnull=False
            ).count()
            if parts_order_count:
                status = 'order_part'
                if parts_send_count:
                    if parts_send_count == parts_send_count:
                        status = 'part_send_all'
                    else:
                        status = 'part_send_few'
        return status


class ReportsParts(ChangeloggableMixin, models.Model):
    title = models.CharField(max_length=250, verbose_name='Наименование')
    price = models.IntegerField(null=True, blank=True, verbose_name='Цена')
    count = models.IntegerField(null=True, verbose_name='Количество')
    document = models.CharField(
        null=True,
        blank=True,
        max_length=250,
        verbose_name='Реквизиты накладной',
    )
    record = models.ForeignKey(
        ReportsRecords, verbose_name='Отчет', on_delete=models.CASCADE
    )
    order_date = models.DateField(
        null=True, verbose_name='Дата заказа', blank=True
    )
    send_date = models.DateField(
        null=True, verbose_name='Дата отправки', blank=True
    )
    send_number = models.CharField(
        null=True, max_length=250, verbose_name='Номер РПО', blank=True
    )

    class Meta:
        verbose_name = 'Деталь из ремонта'
        verbose_name_plural = 'Детали из ремонта'
        ordering = ['record', 'title']

    def __str__(self):
        return self.title


class RecordMembers(models.Model):

    record = models.ForeignKey(
        ReportsRecords, on_delete=models.CASCADE, verbose_name='Запись'
    )
    text = models.TextField(verbose_name='Текст заметки')
    for_user = models.BooleanField(default=False, verbose_name='Для клиента')
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name='Дата создания'
    )
    author = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Автор'
    )

    class Meta:
        verbose_name = 'Заметка к ремонту'
        verbose_name_plural = 'Заметки к ремонтам'
        ordering = [
            '-created_at',
        ]

    def __str__(self):
        return f'{self.author} {self.created_at.strftime("%d %m %Y")}'


@receiver(pre_save, sender=Reports)
def report_pre_save(sender, instance, **kwargs):
    from .views import SendReportSatus

    # получаем все записи этого отчета
    qset = instance.reportsrecords_set.all()
    if qset:
        # подсчитываем итоги
        instance.records_count = qset.count()
        result = qset.aggregate(total_sum=Sum('total_cost'))
        instance.total_cost = result['total_sum']
        result = qset.aggregate(parts_sum=Sum('parts_cost'))
        instance.total_part = result['parts_sum']
        result = qset.aggregate(work_sum=Sum('work_cost'))
        instance.total_work = result['work_sum']
        result = qset.aggregate(move_sum=Sum('move_cost'))
        instance.total_move = result['move_sum']
        # устанавливаем флаг наличия записей с ошибками
        if qset.filter(~Q(errors=None)):
            instance.have_fault = True
        else:
            instance.have_fault = False
        instance.verified_count = qset.filter(verified=True).count()
        # если все записи приняты делаем отчет принятым
        if (
            instance.verified_count == instance.records_count
            and instance.status == 'received'
        ):
            instance.status = 'verified'
            email = instance.service_center.user.email
            if email:
                note = '\nПожалуйста, подгрузите скан копии Акта и '\
                      + 'Счета к вашему отчету на сайте.'
                note = (
                    note + '\nЭто позволит нам оплатить ваши услуги быстрее.'
                )
                SendReportSatus(email, instance, note)
    else:
        # если отчет пустой итоги равны нулю
        instance.records_count = 0
        instance.total_cost = 0
        instance.total_part = 0
        instance.total_work = 0
        instance.total_move = 0


@receiver(post_save, sender=ReportsRecords)
def record_post_save(sender, instance, **kwargs):
    instance.report.save()


@receiver(post_delete, sender=ReportsRecords)
def record_post_delete(sender, instance, **kwargs):
    instance.report.save()


@receiver(pre_delete, sender=ReportsRecords)
def record_pre_delete(sender, instance, **kwargs):
    instance.product = None
    instance.model = None


@receiver(post_delete, sender=ReportsParts)
def part_post_delete(sender, instance, **kwargs):

    if not instance.order_date:
        parts = instance.record.reportsparts_set.filter(
            order_date__isnull=True
        )
        parts_cost = 0
        for one_part in parts:
            parts_cost += one_part.count * one_part.price
        instance.record.parts_cost = parts_cost
        instance.record.total_cost = (
            instance.record.parts_cost
            + instance.record.move_cost
            + instance.record.work_cost
        )
        instance.record.save()
    else:
        parts = instance.record.reportsparts_set.filter(
            order_date__isnull=False
        )
        instance.record.order_parts = True if parts.exists() else False
        instance.record.save()
