from django.contrib import messages
from django.contrib.auth.mixins import UserPassesTestMixin
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import models
from django.shortcuts import redirect

#------------------------------------ ДЕКОРАТОРЫ ---------------------------

#ограничение доступадля всех кроме Staff
def staff_validation(user):
    return user.is_active and user.is_staff


#ограничения доступа для всех кроме GeneralStaff
def general_staff_validation(user):
    if user.is_superuser:
        return True
    if user.is_active and user.groups.filter(name='GeneralStaff').exists():
        return True
    return False


#ограничение доступадля всех кроме Superuser
def superuser_validation(user):
    return user.is_superuser


#проверка размера загружаемого файла
def file_size_validation(value): # add this to some file where you can import it from
    limit = 2 * 1024 * 1024
    if value.size > limit:
        raise ValidationError('файл слишком большой')


#ограничение доступадля всех кроме User
def user_validation(user):
    result = user.is_active and (not user.is_staff or user.is_superuser)
    return result


class SuperUserMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_superuser


#ограничение доступадля всех кроме Staff
class StaffUserMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and self.request.user.is_staff


#ограничения доступа для всех кроме GeneralStaff
class GeneralStaffUserMixin(UserPassesTestMixin):
    def test_func(self):
        if self.request.user.is_superuser:
            return True
        if self.request.user.is_active and self.request.user.is_staff and \
               self.request.user.groups.filter(name='GeneralStaff').exists():
            return True
        return False


#ограничение доступадля всех кроме USERa
class UserMixin(UserPassesTestMixin):
    def test_func(self):
        return self.request.user.is_active and (not self.request.user.is_staff or self.request.user.is_superuser)


# миксин для записи действий пользователей (подключается к нужной моделе)
# взято отсюда: https://webdevblog.ru/logirovanie-izmeneniya-dannyh-v-modelyah-django/
class ChangeloggableMixin(models.Model):
    """Значения полей сразу после инициализации объекта"""
    _original_values = None

    class Meta:
        abstract = True

    def __init__(self, *args, **kwargs):
        super(ChangeloggableMixin, self).__init__(*args, **kwargs)

        self._original_values = {
            field.name: getattr(self, field.name)
            for field in self._meta.fields if field.name not in ['added', 'changed'] and hasattr(self, field.name)
        }

    def get_changed_fields(self):
        """
        Получаем измененные данные
        """
        result = {}
        for name, value in self._original_values.items():
            if value != getattr(self, name):
                temp = {}
                temp[self._meta.get_field(name).verbose_name] = getattr(self, name)
                result.update(temp)
        return result