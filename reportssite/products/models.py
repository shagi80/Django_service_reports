from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.urls import reverse
from servicecentres.models import ServiceCenters
from main.my_validators import ChangeloggableMixin
from main.signals import journal_save_handler, journal_delete_handler
from main.business_logic import *

REPAIR_CHOICES = [
    ('none', 'не указывается'),
    ('document', 'выписка документов'),
    ('easy', 'простой'),
    ('middle', 'средний'),
    ('difficult', 'сложный'),
    ('very_difficult', 'очень сложный'),
    ('type1', 'специальный 1'),
    ('type2', 'специальный 2'),
    ('type3', 'специальный 3'),
    ('type4', 'специальный 4'),
    ('type5', 'специальный 5'),
    ('type6', 'специальный 6'),
    ('type7', 'специальный 7'),
    ('type8', 'специальный 8'),
    ('type9', 'специальный 9'),
    ('type10', 'специальный 10'),
]


class MainProducts(ChangeloggableMixin, models.Model):
    title = models.CharField(max_length=50, unique=True, verbose_name='Наименование')
    short_title = models.CharField(max_length=20, null=True, blank=True, unique=True, verbose_name='Краткое наименование')
    valid_date = models.DateField(null=True, blank=True, verbose_name='Дата начала проверки производства')
    guarantee_period = models.IntegerField(default=1, verbose_name='Гарантийный срок')
    check_serial = models.BooleanField(default=False, blank=True, verbose_name='Проверять серийный номер')

    class Meta():
        verbose_name = 'Вид продуктции'
        verbose_name_plural = 'Виды продуктции'
        ordering = ['title']

    def __str__(self):
        return self.title


class Models(ChangeloggableMixin, models.Model):
    title = models.CharField(max_length=50, unique=True, verbose_name='Наименование')
    code_chars = models.CharField(max_length=10, null=True, blank=True, verbose_name='Буквенная кодировка')
    west_id = models.IntegerField(null=True, blank=True, verbose_name='Цифровая кодировка Запад')
    east_id = models.IntegerField(null=True, blank=True, verbose_name='Цифровая кодировка Восток')
    product = models.ForeignKey(MainProducts, null=True, related_name='parent_product', on_delete=models.PROTECT, verbose_name='Вид продукции')

    class Meta():
        verbose_name = 'Модель продукции'
        verbose_name_plural = 'Модели продукции'
        ordering = ['product', 'title']

    def __str__(self):
        return self.title


class Codes(ChangeloggableMixin, models.Model):
    product = models.ForeignKey(MainProducts, null=True, blank=True, related_name='code_product', on_delete=models.CASCADE, verbose_name='Вид продукции')
    parent = models.ForeignKey('self', limit_choices_to={'is_folder': True}, blank=True, null=True, related_name='parent_code', on_delete=models.CASCADE, verbose_name='Группа дефектов')
    is_folder = models.BooleanField(blank=True, verbose_name='Это группа')
    code = models.CharField(max_length=5, verbose_name='Код ошибки')
    title = models.CharField(max_length=150, verbose_name='Описание ошибки')
    repair_type = models.CharField(max_length=50, choices=REPAIR_CHOICES, verbose_name='Вид ремонта')
    is_active = models.BooleanField(default=True, verbose_name='Используется')

    class Meta():
        verbose_name = 'Код неисправиности'
        verbose_name_plural = 'Коды неисправностей'
        ordering = ['product', 'code']

    def __str__(self):
        return self.code + ' ' + self.title

    def clean(self):
        ABC = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        #parent
        if self.is_folder and self.parent:
            raise ValidationError('Для группы родителькая группа не указывается!')
        if not self.is_folder and not self.parent:
            raise ValidationError('Укажите родительскую группу!')
        if self.parent and self.product and self.product != self.__class__.objects.get(pk=self.parent_id).product:
            raise ValidationError('Группа кодов не принадлежит выбранной продукции!')
        #code
        if self.is_folder:
            if len(self.code) > 1:
                raise ValidationError('Для группы длина кода должна бвть не более одного символа!')
            if self.code not in ABC:
                raise ValidationError('Код должен быть заглавной буквой латинского алфавита!')
        else:
            if self.product:
                if self.code[0] not in ABC:
                    raise ValidationError('Код должен начинаиться с заглавной буквы латинского алфавита!')
                if len(self.code) <= 1:
                    raise ValidationError('Код элемента должен быть длинее одного символа!')
                elif not self.code[1:].isdigit():
                    raise ValidationError('Неверный формат кода! Например: "А123"!')
            else:
                if len(self.code) > 1:
                    raise ValidationError('Для для общих кодов длина должна бвть не более одного символа!')
                if not self.code.isdigit():
                    raise ValidationError('Общие коды состоят только из цифр !')
        #тип ремонта
        if self.is_folder:
            if self.repair_type != 'none':
                raise ValidationError('Для группы кодов тип ремонта не указывается!')
        #Уникальность записи
        if self.is_active and self.__class__.objects.filter(product=self.product, code=self.code).exclude(pk=self.pk):
            raise ValidationError('Для этой продукции уже существует такой же активный код!')

    def get_absolute_url(self):
        return reverse('code_update_page', kwargs={"pk": self.pk})


class BasePrice(ChangeloggableMixin, models.Model):
    product = models.ForeignKey(MainProducts, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Вид продукции')
    price_type = models.CharField(choices=BASE_PRICE_TYPE, max_length=100, verbose_name='Тип прайса', default=PRICE_LITE)
    repair_type = models.CharField(max_length=50, choices=REPAIR_CHOICES, verbose_name='Вид ремонта')
    price = models.IntegerField(default=0, verbose_name='Расценка', validators=[MinValueValidator(limit_value=1,
                                message='Расценка должна быть больше чем ноль !'), ])

    class Meta():
        verbose_name = 'Базовая расценка>'
        verbose_name_plural = 'Базовые расценки'
        ordering = ['product', 'price_type', 'repair_type']

    def __str__(self):
        if self.product and self.product.title:
            return self.product.title + ' ' + self.get_price_type_display + ' ' + self.get_repair_type_display + ' ' + str(self.price)
        else:
            return 'Для всей прдукции ' + ' ' + self.get_price_type_display + ' ' + self.get_repair_type_display + ' ' + str(self.price)

    def get_absolute_url(self):
        return reverse('price_update_page', kwargs={"pk": self.pk})


class CentersPrices(ChangeloggableMixin, models.Model):
    service_center = models.ForeignKey(ServiceCenters, on_delete=models.CASCADE, verbose_name='Сервисный центр')
    product = models.ForeignKey(MainProducts, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Вид продукции')
    group = models.ForeignKey(Codes, related_name="price_parent_group", on_delete=models.CASCADE, verbose_name='Группа дефектов')
    code = models.ForeignKey(Codes, on_delete=models.CASCADE, verbose_name='Код неисправности')
    price = models.IntegerField(default=0, verbose_name='Расценка', validators=[MinValueValidator(limit_value=1,
                                message='Расценка должна быть больше чем ноль !'), ])

    class Meta():
        verbose_name = 'Индивидуальная расценка>'
        verbose_name_plural = 'Индивидуальные расценки'
        ordering = ['service_center', 'product', 'group', 'code']

    def __str__(self):
        return self.service_center.title + ' ' + self.code.code + ' ' + self.code.title + ' ' + str(self.price)

    def get_absolute_url(self):
        return reverse('center_price_page', kwargs={"pk": self.pk, })
        
        
class Production(models.Model):
    date = models.DateTimeField(verbose_name='Дата и время производства')
    type_pk = models.IntegerField(default=0, verbose_name='PK типа продукции')
    code = models.CharField(max_length=50, unique=False, verbose_name='Код')
    shop = models.CharField(max_length=255, verbose_name='Производственное подразделение')

    def __str__(self):
        return f'{self.date.verbose_name}: {self.date}\n' +\
               f'{self.type_pk.verbose_name}: {self.type_pk}' +\
               f'{self.code.verbose_name}: {self.code}' +\
               f'{self.shop.verbose_name}: {self.shop}'


# подключение сигналов для записи измеений
# взято отсюда: https://webdevblog.ru/logirovanie-izmeneniya-dannyh-v-modelyah-django/

post_save.connect(journal_save_handler, sender=Codes)
post_delete.connect(journal_delete_handler, sender=Codes)
post_save.connect(journal_save_handler, sender=BasePrice)
post_delete.connect(journal_delete_handler, sender=BasePrice)
post_save.connect(journal_save_handler, sender=CentersPrices)
post_delete.connect(journal_delete_handler, sender=CentersPrices)
post_save.connect(journal_save_handler, sender=Models)
post_delete.connect(journal_delete_handler, sender=Models)
post_save.connect(journal_save_handler, sender=MainProducts)
post_delete.connect(journal_delete_handler, sender=MainProducts)

