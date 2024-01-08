"""формы приложения статистики"""
from django import forms
from django.contrib.auth.models import User


class MangerWorkFilterForm(forms.Form):
    """фильтр для отчета о работе менеджера"""
    start_date = forms.DateField(required=False, widget=forms.DateInput(format=('%d/%m/%Y'),
                                                                        attrs={'class': 'form-control',
                                                                               'placeholder': 'Select a date',
                                                                               'type': 'date'
                                                                               }))
    end_date = forms.DateField(required=False, widget=forms.DateInput(format=('%d/%m/%Y'),
                                                                      attrs={'class': 'form-control',
                                                                             'placeholder': 'Select a date',
                                                                             'type': 'date'
                                                                             }))
    manager = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True), empty_label="Все менеджеры ...",
                                        required=False, widget=forms.Select(attrs={"class": "form-select"}))
    errors_only = forms.BooleanField(label='только с ошибками', required=False, widget=forms.CheckboxInput(
        attrs={"type": "checkbox", "class": "form-check-input"}))
