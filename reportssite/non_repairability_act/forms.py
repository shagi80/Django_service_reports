import datetime
from typing import Any
from django import forms
from django.forms import inlineformset_factory
from django.db import models
from django.contrib.auth.models import User

from servicecentres.models import ServiceCenters
from main.business_logic import MONTH_CHOICES, YEAR_CHOICES
from products.models import Models, Codes
from main.business_logic import normalize_string
from . import models


class ActEditForm(forms.ModelForm):
    class Meta:
        model = models.NonRepairabilityAct
        fields = '__all__'
        widgets = {
            'model_description': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'serial_number': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'work_type': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'problem_description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': '2'}
            ),
            'completeness': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'client_type': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'client': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'ФИО',
                }
            ),
            'client_phone': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Телефон',
                }
            ),
            'client_addr': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Адрес',
                }
            ),
            'client_email': forms.EmailInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'E-mail',
                }
            ),
            'shop': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Наименование',
                }
            ),
            'shop_phone': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Телефон',
                }
            ),
            'shop_addr': forms.TextInput(
                attrs={
                    'class': 'form-control form-control-sm',
                    'placeholder': 'Адрес',
                }
            ),
            'work_description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': '2'}
            ),
            'decree': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'device_location': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'note': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': '2'}
            ),
            'member_for_user': forms.HiddenInput(),
            'doc_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control-sm',
                    'type': 'date',
                },
            ),
            'buy_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control-sm',
                    'type': 'date',
                },
            ),
            'receipt_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control-sm',
                    'type': 'date',
                },
            ),
            'center': forms.HiddenInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'product': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'model': forms.Select(
                attrs={'class': 'form-select form-select-sm', 'hidden': 'true'}
            ),
            'code': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
        }

    def __init__(self, user=None, disabled=None, *args, **kwargs):
        super(ActEditForm, self).__init__(*args, **kwargs)
        if not self.instance.pk:
            self.fields['center'].queryset = ServiceCenters.objects.filter(
                user=user
            )
            self.initial['center'] = self.fields['center'].queryset.first()
        else:
            self.fields['center'].queryset = ServiceCenters.objects.filter(
                pk=self.instance.center.pk
            )

        self.fields['model'].queryset = Models.objects.none()
        self.fields['code'].queryset = Codes.objects.none()
        # раз по умолчанию в полях пусто - надо создать списки допустимых значений
        # иначе будет ошибка валидации
        if 'product' in self.data and self.data.get('product'):
            product_id = int(self.data.get('product'))
            self.fields['model'].queryset = Models.objects.filter(
                product_id=product_id
            ).order_by('title')
            self.fields['code'].queryset = Codes.objects.filter(
                product_id=product_id
            ).order_by('code')
        elif self.instance.pk and self.instance.product:
            self.fields[
                'model'
            ].queryset = self.instance.product.parent_product.all()
            self.fields[
                'code'
            ].queryset = self.instance.product.code_product.all()
        # блокировка полей формы при необходимости
        if disabled:
            for field in self.fields:
                self.fields[field].disabled = True

    def clean_serial_number(self):
        """Нормализация серийного номера."""
        serial = self.cleaned_data.get('serial_number', '')
        return normalize_string(serial) if serial else None


ActFileFormset = inlineformset_factory(
    models.NonRepairabilityAct,
    models.ActDocumnent,
    extra=1,
    fields='__all__',
    widgets={
        'title': forms.Select(attrs={'class': 'form-select form-select-sm'}),
        'number': forms.TextInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
        'date': forms.DateInput(
            format=('%Y-%m-%d'),
            attrs={'class': 'form-control form-control-sm', 'type': 'date'},
        ),
        'file': forms.FileInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
    },
)


class ActsFilterForm(forms.Form):

    SEVICE_CHOICES = tuple(
        ServiceCenters.objects.all().values_list('pk', 'title')
    )

    filter = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-sm',
                'placeholder': 'клинет/продавец/номер',
            }
        ),
    )

    service_center = forms.IntegerField(
        required=False,
        widget=forms.Select(
            choices=(('', 'все сервисы ...'),) + SEVICE_CHOICES,
            attrs={'class': 'form-select form-select-sm'},
        ),
    )
    month = forms.IntegerField(
        initial=datetime.datetime.now().month,
        required=False,
        widget=forms.Select(
            choices=(('', '...'),) + MONTH_CHOICES,
            attrs={'class': 'form-select form-select-sm'},
        ),
    )
    year = forms.IntegerField(
        initial=datetime.datetime.now().year,
        required=False,
        widget=forms.Select(
            choices=[
                ('', '...'),
            ]
            + YEAR_CHOICES,
            attrs={'class': 'form-select form-select-sm'},
        ),
    )
    status = forms.ChoiceField(
        choices=[
            ('', 'все статусы ...'),
        ]
        + models.ActStatus.choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    staff_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        empty_label='все менеджеры ...',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
