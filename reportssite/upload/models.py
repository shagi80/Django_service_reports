""" модели загружаемых файлов  """
from os.path import splitext
from uuid import uuid4
from django.db import models
from django.core.validators import FileExtensionValidator
from reports.models import Reports, ReportsRecords


# виды документов? прилагаемых к отчету
REPORT_ACT = 'act'
REPORT_INVOICE = 'invoice'
REPORT_NETTING = 'netting'
OTHER = 'other'

REPORT_DOCUMENT = (
    (REPORT_ACT, 'Акт'),
    (REPORT_INVOICE, 'Счет'),
    (REPORT_NETTING, 'Акт взаимозачета'),
    (OTHER, 'Другое')
)


def document_name(instance, filename):
    """ функция генерации пути сохранения медиафайла """
    return f'report_document/{str(instance.report.pk)}/{uuid4().hex}{splitext(filename)[1]}'


class ReportDocumnent(models.Model):
    """ документ отчета """

    report = models.ForeignKey(
        Reports, verbose_name='Отчет', on_delete=models.CASCADE, null=False, blank=False)
    title = models.CharField(
        choices=REPORT_DOCUMENT, verbose_name='Наименование документа', max_length=20, null=False, blank=False)
    number = models.CharField(
        verbose_name='Номер документа', max_length=20, null=False, blank=False)
    date = models.DateField(
        verbose_name='Дата документа', null=False, blank=False)
    file = models.FileField(
        verbose_name='Файйл документа', upload_to=document_name, null=False, blank=False,
        validators=[FileExtensionValidator( ['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx', 'xls', 'jpeg'] )]
        )

    class Meta():
        verbose_name = 'Документ отчета'
        verbose_name_plural = 'Документы отчетов'
        ordering = ['report', 'title']


    def __str__(self):
        return f'{self.report} {self.get_title_display()} №{self.number} от {self.date}'
    

    def delete(self, *args, **kwargs):
        """ удаление файла вместе с удалением объекта """
        # До удаления записи получаем необходимую информацию
        storage = self.file.storage
        path = self.file.path
        # Удаляем сначала модель ( объект )
        super(ReportDocumnent, self).delete(*args, **kwargs)
        # Потом удаляем сам файл
        storage.delete(path)


def record_document_name(instance, filename):
    """ функция генерации пути сохранения медиафайла документа ремонта """
    return f'record_document/{str(instance.record.pk)}/{uuid4().hex}{splitext(filename)[1]}'


class RecordDocumnent(models.Model):
    """ документ ремонта """

    record = models.ForeignKey(
        ReportsRecords, verbose_name='Ремонт', on_delete=models.CASCADE, null=False, blank=False)
    title = models.CharField(
        max_length=255, verbose_name='Наименование документа', null=False, blank=False)
    number = models.CharField(
        verbose_name='Номер документа', max_length=20, null=False, blank=False)
    date = models.DateField(
        verbose_name='Дата документа', null=False, blank=False)
    file = models.FileField(
        verbose_name='Файйл документа', upload_to=record_document_name, null=False, blank=False,
        validators=[FileExtensionValidator( ['pdf', 'doc', 'docx', 'jpg', 'png', 'xlsx', 'xls', 'jpeg'] )]
        )

    class Meta():
        verbose_name = 'Документ ремонта'
        verbose_name_plural = 'Документы ремонта'
        ordering = ['record', 'title']


    def __str__(self):
        return f'{self.record.report} {self.record} {self.title} №{self.number} от {self.date}'
    

    def delete(self, *args, **kwargs):
        """ удаление файла вместе с удалением объекта """
        # До удаления записи получаем необходимую информацию
        storage = self.file.storage
        path = self.file.path
        # Удаляем сначала модель ( объект )
        super(RecordDocumnent, self).delete(*args, **kwargs)
        # Потом удаляем сам файл
        storage.delete(path)
