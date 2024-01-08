from django import forms
from django.contrib.auth.models import User
from .models import ServiceRegions, ServiceCenters, ServiceContacts


class CenterFilterForm(forms.Form):
    filter = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'type': "text", 'class': "form-control", 'placeholder': "Наименование/город"}))
    region = forms.ModelChoiceField(queryset=ServiceRegions.objects.all(), empty_label="Все регионы ...",
                                    required=False, widget=forms.Select(attrs={"class": "form-select"}))
    staff_user = forms.ModelChoiceField(queryset=User.objects.filter(is_staff=True), empty_label="Все менеджеры ...",
                                        required=False, widget=forms.Select(attrs={"class": "form-select"}))
    active_only = forms.BooleanField(label='активные', required=False, widget=forms.CheckboxInput(
        attrs={"type": "checkbox", "class": "form-check-input"}))
    self_only = forms.BooleanField(label='свои', required=False, widget=forms.CheckboxInput(
        attrs={"type": "checkbox", "class": "form-check-input"}))


class CenterCreateForm(forms.ModelForm):
    error_css_class = "text-danger text-center"

    #получение значения по умолчанию из VIEW
    def __init__(self, def_user=None, *args, **kwargs):
        super(CenterCreateForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
        # блокировка полей в зависимости от пользователя
        if instance and instance.pk and not def_user.is_superuser and\
                not def_user.groups.filter(name='GeneralStaff').exists():
            self.fields['staff_user'].disabled = True
            self.fields['code'].disabled = True
            self.fields['title'].disabled = True
            self.fields['city'].disabled = True
            self.fields['region'].disabled = True
            self.fields['price_type'].disabled = True

    class Meta:
        model = ServiceCenters
        fields = '__all__'
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введите код по 1С ..."}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введите наименование ..."}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введите город ..."}),
            'region': forms.Select(attrs={'class': 'form-select'}),
            'addr': forms.TextInput(attrs={'class': 'form-control'}),
            'post_addr': forms.TextInput(attrs={'class': 'form-control'}),
            'conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'free_parts': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'user': forms.Select(attrs={'class': 'form-select'}),
            'staff_user': forms.Select(attrs={'class': 'form-select'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
            'price_type': forms.Select(attrs={'class': 'form-select'}),
        }


class ContactCreateForm(forms.ModelForm):
    error_css_class = "text-danger text-center"

    #получение значения по умолчанию из VIEW
    def __init__(self, staff_user=None, *args, **kwargs):
        super(ContactCreateForm, self).__init__(*args, **kwargs)
        if staff_user.is_superuser or staff_user.groups.filter(name='GeneralStaff').exists():
            self.fields['service_center'].queryset = ServiceCenters.objects.all()
        else:
            self.fields['service_center'].queryset = ServiceCenters.objects.filter(staff_user=staff_user)

    class Meta:
        model = ServiceContacts
        fields = '__all__'
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введите ABJ ..."}),
            'funct': forms.TextInput(attrs={'class': 'form-control'}),
            'tel_num': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'note': forms.TextInput(attrs={'class': 'form-control'}),
            'service_center': forms.Select(attrs={'class': 'form-select'}),
        }

