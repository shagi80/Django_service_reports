from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_save, post_delete
from django.urls import reverse
from main.my_validators import ChangeloggableMixin
from main.signals import journal_save_handler, journal_delete_handler
from main.business_logic import BASE_PRICE_TYPE, PRICE_LITE


class ServiceRegions(ChangeloggableMixin, models.Model):
    title = models.CharField(max_length=50, db_index=True, verbose_name='Наименование')
    staff_user = models.ForeignKey(User, blank=True,  null=True, on_delete=models.SET_NULL, verbose_name='Менеджер', limit_choices_to={'is_staff': True})

    # def get_absolute_url(self):
    #    return reverse('news_page', kwargs={"pk": self.pk})

    class Meta():
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'
        ordering = ['title']

    def __str__(self):
        return self.title


class ServiceCenters(ChangeloggableMixin, models.Model):
    code = models.CharField(max_length=50, db_index=True, verbose_name='Код', help_text='Код по 1С. Обязательное поле.')
    title = models.CharField(max_length=50, db_index=True, verbose_name='Наименование', help_text='Юридическое наименование. Обязательное поле.')
    city = models.CharField(max_length=50, verbose_name='Город', help_text='Город. Обязательное поле.')
    region = models.ForeignKey(ServiceRegions,  null=True,on_delete=models.PROTECT, verbose_name='Регион', help_text='Регион СЦ. Обязательное поле.')
    addr = models.CharField(max_length=350, blank=True, verbose_name='Адрес')
    post_addr = models.CharField(max_length=350, blank=True, verbose_name='Почтовый адрес')
    conditions = models.TextField(blank=True, verbose_name='Особыче условия')
    free_parts = models.BooleanField(default=False, verbose_name='Бесплатные запчасти')
    grade = models.FloatField(default=5, verbose_name='Рэйтинг', editable=False)
    note = models.TextField(blank=True, verbose_name='Примечание')
    is_active = models.BooleanField(default=True, verbose_name='Ативен')
    user = models.ForeignKey(User, related_name='user_centers', blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Пользователь', limit_choices_to={'is_staff': False})
    staff_user = models.ForeignKey(User, related_name='staff_centers', blank=True, null=True, on_delete=models.SET_NULL, verbose_name='Менеджер', limit_choices_to={'is_staff': True})
    price_type = models.CharField(choices=BASE_PRICE_TYPE, max_length=100, verbose_name='Тип прайса',
                                  default=PRICE_LITE)

    def get_absolute_url(self):
        return reverse('centres_update_page', kwargs={"pk": self.pk})

    class Meta():
        verbose_name = 'Сервисный центр'
        verbose_name_plural = 'Сервисные центры'
        ordering = ['title']

    def __str__(self):
        return self.title

    def clean(self):
        if self.code and self.__class__.objects.filter(code=self.code).exclude(pk=self.pk):
            raise ValidationError("Обьект с таким кодом 1С уже существует!")


class ServiceContacts(ChangeloggableMixin, models.Model):
    name = models.CharField(max_length=150, db_index=True, verbose_name='Фамилия, имя, отчетство')
    service_center = models.ForeignKey(ServiceCenters, on_delete=models.CASCADE, verbose_name='Сервисный центр')
    funct = models.CharField(max_length=150, blank=True, verbose_name='Должность')
    tel_num = models.CharField(max_length=50, blank=True, verbose_name='Телефон')
    email = models.EmailField(blank=True, verbose_name='E-mail')
    note = models.CharField(max_length=350, blank=True, verbose_name='Примечание')

    class Meta():
        verbose_name = 'Контакт'
        verbose_name_plural = 'Контакты'
        ordering = ['service_center__title', 'name']

    def get_absolute_url(self):
        return reverse('contact_update_page', kwargs={"pk": self.pk})

    def __str__(self):
        return self.name


class ServiceMember(models.Model):
    text = models.CharField(
        max_length=1000, help_text='Текст замечания'
    )

    update_at = models.DateTimeField(auto_now=True)

    status = models.PositiveSmallIntegerField(default=3, help_text='Статус')

    center = models.ForeignKey(
        'ServiceCenters', on_delete=models.CASCADE, related_name='members'
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Замечание к сервису'
        verbose_name_plural = 'Замечания к сервисам'
        ordering = ['status', 'update_at']

    def __str__(self):
        return (
            f'{self.center} Замечание "{str(self.text)[:30]}" '
            f'обновлено {self.update_at.strftime("%Y-%m-%d %H:%M:%S")} '
            f'пользователем {self.user}.'
        )


post_save.connect(journal_save_handler, sender=ServiceRegions)
post_delete.connect(journal_delete_handler, sender=ServiceRegions)
post_save.connect(journal_save_handler, sender=ServiceCenters)
post_delete.connect(journal_delete_handler, sender=ServiceCenters)
post_save.connect(journal_save_handler, sender=ServiceContacts)
post_delete.connect(journal_delete_handler, sender=ServiceContacts)