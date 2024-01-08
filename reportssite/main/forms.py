from django.contrib.auth.forms import AuthenticationForm
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core import validators
from .my_validators import file_size_validation
from .models import TYPE_MODEL, TYPE_ACTION_ON_MODEL
from servicecentres.models import ServiceCenters


#форма входя на портал
class UserLoginForm(AuthenticationForm):
    username = forms.CharField(label='Имя', widget=forms.TextInput(attrs={'class': 'form-control', 'id': 'floatingInput'}))
    password = forms.CharField(label='Пароль', widget=forms.PasswordInput(attrs={'class': 'form-control', 'id': 'floatingPassword'}))


class DataFileLoadForm(forms.Form):
    file = forms.FileField(label='FileField', validators=[validators.FileExtensionValidator(['txt']), file_size_validation])


class LogsFilterForm(forms.Form):
    MODELS = list(TYPE_MODEL)
    MODELS.insert(0, ('empty', 'Все типы ...'))
    MODELS = tuple(MODELS)
    ACTIONS = list(TYPE_ACTION_ON_MODEL)
    ACTIONS.insert(0, ('empty', 'Все действия ...'))
    ACTIONS = tuple(ACTIONS)
    model = forms.ChoiceField(choices=MODELS, required=False, widget=forms.Select(attrs={'class': "form-select"}))
    action_on_model = forms.ChoiceField(choices=ACTIONS, required=False, widget=forms.Select(attrs={'class': "form-select"}))
    staff_user = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True), empty_label="Все менеджеры ...",
                                        required=False, widget=forms.Select(attrs={"class": "form-select"}))

