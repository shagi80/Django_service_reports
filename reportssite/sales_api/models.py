from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.conf import settings


class Counterparty(models.Model):
    company_name = models.CharField(max_length=255, verbose_name='Наименование организации')
    inn = models.CharField(max_length=12, unique=True, verbose_name='ИНН')
    code = models.CharField(max_length=20, unique=True, verbose_name='Код')

    class Meta:
        verbose_name = 'Контрагент'
        verbose_name_plural = 'Контрагенты'

    def __str__(self):
        return f"{self.company_name} (ИНН: {self.inn})"


class EmployeeProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Пользователь'
    )
    counterparty = models.ForeignKey(
        Counterparty,
        on_delete=models.CASCADE,
        related_name='employees',
        verbose_name='Контрагент'
    )


class Storage(models.Model):
    """Storage"""

    code = models.CharField(max_length=20, unique=True, verbose_name='Код', db_index=True)
    name = models.CharField(max_length=150, verbose_name='Наименование')
    city = models.CharField(max_length=50, verbose_name='Город')
    addr = models.CharField(max_length=50, blank=True, null=True, verbose_name='Адрес')
    contact = models.CharField(max_length=300, blank=True, null=True, verbose_name='Контакт')
    work_time = models.CharField(max_length=300, blank=True, null=True, verbose_name='Режим работы')
    note = models.CharField(max_length=300, blank=True, null=True, verbose_name='Дополнительно')

    class Meta:
        verbose_name = 'Склад'
        verbose_name_plural = 'Склады'
        ordering = ['name']

    def __str__(self):
        return (f'{self.name} ({self.city})' )


class Group(models.Model):
    """Nomenclature group"""

    code = models.CharField(max_length=20, unique=True, verbose_name='Код', db_index=True)
    owner_code = models.CharField(max_length=20, verbose_name='Код владельца')
    name = models.CharField(max_length=150, verbose_name='Наименование')

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        verbose_name = 'Группа номенклатуры'
        verbose_name_plural = 'Группы номенклатуры'
        ordering = ['owner_code', 'name']

    def __str__(self):
        return (f'{self.name} ({self.code})' )


class GoodsItem(models.Model):
    """Nomenclature item"""

    code = models.CharField(max_length=20, unique=True, verbose_name='Код', db_index=True)
    owner_code = models.CharField(max_length=20, verbose_name='Код владельца', db_index=True)
    name = models.CharField(max_length=150, verbose_name='Наименование')
    unit_code = models.IntegerField(blank=False, null=False, verbose_name='Код единицы',
                                    validators=[MinValueValidator(0), MaxValueValidator(1000)])
    unit_name = models.CharField(max_length=50, blank=False, null=False, verbose_name='Наименование единицы')

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        verbose_name = 'Номенклатура'
        verbose_name_plural = 'Номенклатура'
        ordering = ['name']

    def __str__(self):
        return (f'{self.name} ({self.code})' )


class Remnant(models.Model):
    """Goods remanats"""

    storage_code = models.CharField(max_length=20, verbose_name='Код склада', db_index=True)
    item_code = models.CharField(max_length=20, verbose_name='Код', db_index=True)
    count = models.IntegerField(blank=True, null=True, verbose_name='Количество', default=0)

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        verbose_name = 'Остаток на складе'
        verbose_name_plural = 'Остатки на складе'
        ordering = ['storage_code', 'item_code']
        constraints = [
            models.UniqueConstraint(
                fields=['storage_code', 'item_code'],
                name='unique_storage_item_remnant'
            )
        ]

    def __str__(self):
        return (f'{self.storage_code}, {self.item_code} = {self.count}' )


class Price(models.Model):
    """Goods price"""

    counterparty_code = models.CharField(max_length=20, verbose_name='Код Контрагента', db_index=True)
    item_code = models.CharField(max_length=20, verbose_name='Код номенклатуры', db_index=True)
    price = models.IntegerField(blank=True, null=True, verbose_name='Цена', default=0,
                                validators=[MinValueValidator(0)])

    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        verbose_name = 'Цена товара'
        verbose_name_plural = 'Цены товаров'
        ordering = ['counterparty_code', 'item_code']
        constraints = [
            models.UniqueConstraint(
                fields=['counterparty_code', 'item_code'],
                name='unique_counterparty_item_price'
            )
        ]

    def __str__(self):
        return (f'{self.counterparty_code}, {self.item_code} = {self.price}' )
