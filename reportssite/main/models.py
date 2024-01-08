from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db import models


def get_name(self):
    result = None
    if self:
        if self.last_name or self.first_name:
            if self.last_name:
                if self.first_name:
                    result = self.last_name+' '+self.first_name[0]
                else:
                    result = self.last_name
            else:
                result = self.first_name
        else:
            result = self.username
        return result
    return result


def get_service_center(self):
    from servicecentres.models import ServiceCenters
    try:
        center = ServiceCenters.objects.get(user=self, is_active=True)
        return center
    except Exception:
        return None



User.add_to_class("__str__", get_name)

User.add_to_class("service_center", get_service_center)



# модель для записи действий пользователей
# взято отсюда: https://webdevblog.ru/logirovanie-izmeneniya-dannyh-v-modelyah-django/

ACTION_CREATE = 'create'
ACTION_UPDATE = 'update'
ACTION_DELETE = 'delete'

MODEL_CODES = 'Codes'
MODEl_PRODUCT = 'MainProducts'
MODEL_PODUCT_MODELS = 'Models'
MODE_BASE_PRICE = 'BasePrice'
MODEL_CENTER_PRICE = 'CentersPrices'
MODEL_CENTER = 'ServiceCenters'
MODEL_CONTACT = 'ServiceContacts'
MODEL_REGIONS = 'ServiceRegion'


TYPE_MODEL = (
    (MODEl_PRODUCT, 'тип продукции'),
    (MODEL_CODES, 'код дефекта'),
    (MODEL_PODUCT_MODELS, 'модель продукции'),
    (MODE_BASE_PRICE, 'базовая расценка'),
    (MODEL_CENTER_PRICE, 'индивидуальная расценка'),
    (MODEL_REGIONS, 'регион'),
    (MODEL_CENTER, 'севиснвый центр'),
    (MODEL_CONTACT, 'контакт'),
)

TYPE_ACTION_ON_MODEL = (
    (ACTION_CREATE, 'Создание'),
    (ACTION_UPDATE, 'Изменение'),
    (ACTION_DELETE, 'Удаление'),
)


class ChangeLogs(models.Model):
    changed = models.DateTimeField(auto_now=True, verbose_name=u'Дата/время изменения')
    model = models.CharField(choices=TYPE_MODEL, max_length=255, verbose_name=u'Таблица', null=True)
    record_id = models.IntegerField(verbose_name=u'ID записи', null=True)
    user = models.ForeignKey(User, verbose_name=u'Автор изменения', on_delete=models.CASCADE, null=True)
    action_on_model = models.CharField(choices=TYPE_ACTION_ON_MODEL, max_length=50, verbose_name=u'Действие', null=True)
    data = models.JSONField(verbose_name=u'Изменяемые данные модели', default=dict)
    ipaddress = models.CharField(max_length=15, verbose_name=u'IP адресс', null=True)

    class Meta:
        ordering = ('-changed',)
        verbose_name = 'Действие пользователя'
        verbose_name_plural = 'Действия пользователей'

    def __str__(self):
        return f'{self.id}'

    @classmethod
    def add(cls, instance, user, ipaddress, action_on_model, data, id=None):
        #Создание записи в журнале регистрации изменений
        log = ChangeLogs.objects.get(id=id) if id else ChangeLogs()
        log.model = instance.__class__.__name__
        log.record_id = instance.pk
        if user:
            log.user = user
        log.ipaddress = ipaddress
        log.action_on_model = action_on_model
        log.data = data
        log.save()
        return log.pk