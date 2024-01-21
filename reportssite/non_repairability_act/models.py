import datetime
from os.path import splitext
from uuid import uuid4
from django.db import models
from django.urls import reverse_lazy
from django.utils import timezone
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import User

from main.business_logic import WORKTYPE
from reports.models import ReportsRecords
from main.business_logic import parse_serial
from reports.models import ClientType


class DeviceLocation(models.TextChoices):
    CLIENT = (
        'client',
        'выдать клиенту для предъявления в торгующую организацию',
    )
    WORKSHOP = 'workshop', 'оставить в сервисном центре для разбора'
    MANUFACTURE = 'manufacture', 'вернуть производителю'


class ActStatus(models.TextChoices):
    DRAFT = 'draft', 'черновик'
    SEND = 'send', 'отправлен на проверку'
    REFINEMENT = 'refinement', 'на доработке'
    SEND_AGAIN = 'send_again', 'отправлен повторно'
    RECEIVED = 'received', 'на проверке'
    ACCEPTED = 'accepted', 'принят на рассмотрение'
    CONFIRMED = 'confirmed', 'подтвержден'
    COMPENSATED = 'compensated', 'компенсирован'


class DocumentType(models.TextChoices):
    CHECK = 'check', 'Чек/накладная'
    PHOTO = 'photo', 'Фото'
    CLAIM = 'claim', 'Претензия'
    OTHER = 'other', 'Другое'


class ActStatusHistory(models.Model):
    act = models.ForeignKey(
        'NonRepairabilityAct',
        on_delete=models.CASCADE,
        related_name='statuses',
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        choices=ActStatus.choices, max_length=20, default=ActStatus.DRAFT
    )

    class Meta:
        verbose_name = 'Статус акта'
        verbose_name_plural = 'Статусы актов'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'{self.act} Cтатус "{self.get_status_display()}" '
            f'установлен {self.created_at.strftime("%Y-%m-%d %H:%M:%S")} '
            f'пользователем {self.user}.'
        )


class ActMember(models.Model):
    text = models.CharField(
        max_length=1000, default=ActStatus.DRAFT, help_text='Текст замечания'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    for_center = models.BooleanField(
        default=False, blank=True, help_text='Замечание для СЦ'
    )

    act = models.ForeignKey(
        'NonRepairabilityAct', on_delete=models.CASCADE, related_name='members'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Замечание к акту'
        verbose_name_plural = 'Замечания к актам'
        ordering = ['-created_at']

    def __str__(self):
        return (
            f'{self.act} Замечание "{str(self.text)[:30]}" '
            f'добавлено {self.created_at.strftime("%Y-%m-%d %H:%M:%S")} '
            f'пользователем {self.user}.'
        )


def document_name(instance, filename):
    """функция генерации пути сохранения медиафайла"""

    return f'act_document/{str(instance.act.pk)}/{uuid4().hex}\
        {splitext(filename)[1]}'


class ActDocumnent(models.Model):
    """документ акт"""

    title = models.CharField(
        choices=DocumentType.choices,
        max_length=20,
        help_text='Наименование документа',
    )
    number = models.CharField(max_length=20, help_text='Номер документа')
    file = models.FileField(
        upload_to=document_name,
        validators=[
            FileExtensionValidator(
                ['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx', 'xls', 'jpeg']
            )
        ],
    )

    date = models.DateField(help_text='Дата документа')

    act = models.ForeignKey(
        'NonRepairabilityAct',
        on_delete=models.CASCADE,
        related_name='documents',
    )

    class Meta:
        verbose_name = 'Документ акта'
        verbose_name_plural = 'Документы актов'
        ordering = ['act', 'title']

    def __str__(self):
        return f'{self.act} {self.get_title_display()}\
              №{self.number} от {self.date}.'

    def delete(self, *args, **kwargs):
        """удаление файла вместе с удалением объекта"""
        # До удаления записи получаем необходимую информацию
        storage = self.file.storage
        path = self.file.path
        # Удаляем сначала модель ( объект ) и потом удаляем сам файл
        super(ActDocumnent, self).delete(*args, **kwargs)
        storage.delete(path)


class NonRepairabilityAct(models.Model):
    model_description = models.CharField(
        max_length=150, null=True, blank=True, help_text='Модель продукции'
    )
    serial_number = models.CharField(
        max_length=30, null=True, blank=True, help_text='Серийный  номер'
    )
    work_type = models.CharField(
        choices=WORKTYPE,
        max_length=50,
        null=True,
        blank=True,
        help_text='Тип ремонта',
    )
    completeness = models.CharField(
        max_length=1000, blank=True, null=True, help_text='Комплектация'
    )
    problem_description = models.CharField(
        max_length=1000, blank=True, null=True, help_text='Заявленный дефект'
    )
    client_type = models.CharField(
        choices=ClientType.choices,
        max_length=50,
        blank=True,
        null=True,
        help_text='Тип клиента',
    )
    client = models.CharField(
        max_length=150, blank=True, null=True, help_text='ФИО клиента'
    )
    client_phone = models.CharField(
        max_length=150, blank=True, null=True, help_text='Телефон клиента'
    )
    client_addr = models.CharField(
        max_length=350, blank=True, null=True, help_text='Адрес клиента'
    )
    client_email = models.EmailField(
        max_length=500, blank=True, null=True, help_text='E-mail клиента'
    )
    shop = models.CharField(
        max_length=150,
        blank=True,
        null=True,
        help_text='Наименование продавца',
    )
    shop_phone = models.CharField(
        max_length=150, blank=True, null=True, help_text='Телефон продавца'
    )
    shop_addr = models.CharField(
        max_length=350, blank=True, null=True, help_text='Адрес продавца'
    )
    work_description = models.CharField(
        max_length=1000,
        blank=True,
        null=True,
        help_text='Выявленная неиспраность',
    )
    decree = models.CharField(
        max_length=250, blank=True, null=True, help_text='Заключение'
    )
    device_location = models.CharField(
        choices=DeviceLocation.choices,
        max_length=350,
        blank=True,
        null=True,
        help_text='Местонахождение изделия',
    )
    note = models.CharField(
        max_length=2000, blank=True, null=True, help_text='Примечание'
    )
    member_for_user = models.CharField(
        max_length=1000, blank=True, null=True, help_text='Заметка для сервиса'
    )

    doc_date = models.DateField(null=True, help_text='Дата документа')
    buy_date = models.DateField(
        null=True, blank=True, help_text='Дата покупки'
    )
    receipt_date = models.DateField(
        null=True, blank=True, help_text='Дата приемки'
    )

    center = models.ForeignKey(
        'servicecentres.ServiceCenters',
        on_delete=models.CASCADE,
        related_name='non_repairability_acts',
    )
    product = models.ForeignKey(
        'products.MainProducts',
        on_delete=models.SET_NULL,
        related_name='non_repairability_acts',
        null=True,
        blank=True,
        help_text='Вид продукции',
    )
    model = models.ForeignKey(
        'products.Models',
        on_delete=models.SET_NULL,
        related_name='non_repairability_acts',
        default=None,
        null=True,
        blank=True,
        help_text='Модель продукции',
    )
    code = models.ForeignKey(
        'products.Codes',
        on_delete=models.SET_NULL,
        related_name='non_repairability_acts',
        default=None,
        null=True,
        blank=True,
        help_text='Код дефекта',
    )

    class Meta:
        verbose_name = 'Акт неремонтопригодности'
        verbose_name_plural = 'Акты неремонтопригодности'
        ordering = ['-doc_date']

    def __str__(self):
        return f'Акт НРП №{self.pk} от {self.doc_date}.\
              {self.center}({self.center.city}).'

    def get_absolute_url(self):
        return reverse_lazy('act-user-update', kwargs={'pk': self.pk})

    @property
    def status(self):
        return self.statuses.filter(act=self).first()

    @property
    def repairs(self):
        return ReportsRecords.objects.filter(
            product=self.product, serial_number__iexact=self.serial_number
        ).values(
            'report__service_center__pk',
            'report__service_center__title',
            'report__service_center__city',
            'report__status',
            'pk',
            'end_date',
            'code__code',
            'code__title',
        )

    def add_status(self, new_status, user):
        if not self.status or (self.status.status != new_status):
            ActStatusHistory.objects.create(
                act=self,
                user=user,
                created_at=timezone.now(),
                status=new_status,
            )

    def add_member(self, text, for_center, user):
        ActMember.objects.create(
            act=self,
            user=user,
            created_at=timezone.now(),
            text=text,
            for_center=for_center,
        )

    def delete_member(self, member_pk):
        self.members.get(pk=member_pk).delete()

    @property
    def send_errors(self):
        REQUIRED_FIELDS = 'Обязательное поле !'

        result = {}

        def add_error(field, text):
            if field in result:
                result[field].append(text)
            else:
                result[field] = [text]

        def check_client_data():
            if not self.client:
                add_error('client', 'ФИО клиента - обязательное поле !')
            if not self.client_addr:
                add_error('client', 'Адрес клиента - обязательное поле !')
            if not self.client_phone:
                add_error('client', 'Телефон клиента - обязательное поле !')

        if not self.product:
            result['product'] = [
                REQUIRED_FIELDS,
            ]
        if not self.model_description:
            result['model_description'] = [
                REQUIRED_FIELDS,
            ]
        if not self.serial_number:
            result['serial_number'] = [
                REQUIRED_FIELDS,
            ]
        elif self.product and self.product.check_serial and self.model:
            serial_data = parse_serial(self.model, self.serial_number)
            if 'error' in serial_data:
                result['serial_number'] = [
                    serial_data['error'],
                ]
        if not self.problem_description:
            result['problem_description'] = [
                REQUIRED_FIELDS,
            ]
        if not self.problem_description:
            result['problem_description'] = [
                REQUIRED_FIELDS,
            ]
        if not self.receipt_date:
            result['receipt_date'] = [
                'Дата приема - обязательное поле !',
            ]
        else:
            if self.receipt_date > datetime.datetime.now().date():
                result['receipt_date'] = [
                    'Дата поступления в ремонт позднее сегодняшней даты !',
                ]
        if not self.client_type:
            add_error('client', 'Тип клиента - обязательное поле !')
        else:
            if self.client_type == 'organization' and not self.client_email:
                add_error(
                    'client',
                    'Для клиента-организации e-mail - обязательное поле !',
                )
                check_client_data()
        if not self.work_type:
            result['work_type'] = [
                REQUIRED_FIELDS,
            ]
        else:
            if self.work_type == 'warranty':
                if self.client_type != 'organization':
                    check_client_data()
                if not self.buy_date:
                    add_error(
                        'receipt_date', 'Дата продажи - обязательное поле !'
                    )
                else:
                    if self.buy_date > datetime.datetime.now().date():
                        add_error(
                            'receipt_date',
                            'Дата продажи позднее сегодняшней даты !',
                        )
                    if self.buy_date > self.receipt_date:
                        add_error(
                            'receipt_date',
                            'Дата продажи позднее даты приема !',
                        )
            else:
                if self.client_type != 'organization':
                    add_error(
                        'client',
                        'Для предторгового ремонта клиент не может быть\
                              физлицом !',
                    )
        if not self.shop:
            result['shop'] = [
                REQUIRED_FIELDS,
            ]
        if not self.shop_addr:
            add_error('shop', 'Адрес продавца - обязательное поле !')
        if not self.shop_phone:
            add_error('shop', 'Телефон продавца - обязательное поле !')
        if not self.work_description:
            result['work_description'] = [
                REQUIRED_FIELDS,
            ]
        if not self.code:
            result['code'] = [
                REQUIRED_FIELDS,
            ]
        if not self.decree:
            result['decree'] = [
                REQUIRED_FIELDS,
            ]
        if not self.documents.exists():
            result[''] = [
                'К Акту должны быть приложены документы !',
            ]

        return result
