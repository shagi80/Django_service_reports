from django import forms
from django.contrib import messages
from django.urls import reverse_lazy
from .models import Codes, BasePrice, CentersPrices, MainProducts
from servicecentres.models import ServiceCenters


class CodeForm(forms.ModelForm):

    class Meta:
        model = Codes
        fields = '__all__'
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'is_folder': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введите код ..."}),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': "Введите описание ..."}),
            'repair_type': forms.Select(attrs={'class': 'form-select'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, code=None, *args, **kwargs):
        # получение аргументов и содержимого
        super(CodeForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        if self.instance and self.instance.pk:
            self.fields['product'].disabled = True
            self.fields['parent'].disabled = True
            self.fields['is_folder'].disabled = True
            self.fields['code'].disabled = True


        #это нужно что бы по умолчанию в полях было пусто
        self.fields['parent'].queryset = Codes.objects.none()

        # раз по умолчанию в полях пусто - надо создать списки допустимых значений иначе будет ошибка валидации
        if 'product' in self.data and self.data.get('product'):
            try:
                product_id = int(self.data.get('product'))
                self.fields['parent'].queryset = Codes.objects.filter(product_id=product_id, is_folder=True, is_active=True).order_by('code')
            except (ValueError, TypeError):
                messages.error(self.request, 'Ошибка получения данных о продукции!')
        elif instance and instance.pk:
            if self.instance.product:
                self.fields['parent'].queryset = self.instance.product.code_product.filter(is_folder=True, is_active=True)
            else:
                self.fields['parent'].queryset = Codes.objects.filter(is_folder=True, product=None, is_active=True)


class PriceForm(forms.ModelForm):

    class Meta:
        model = BasePrice
        fields = '__all__'
        widgets = {
            'product': forms.Select(attrs={'class': 'form-select'}),
            'price_type': forms.Select(attrs={'class': 'form-select'}),
            'repair_type': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-select'}),
        }

    def __init__(self, code=None, price_type=None, *args, **kwargs):
        # получение аргументов и содержимого
        super(PriceForm,self).__init__(*args, **kwargs)
        if code:
            self.initial['product'] = code.product
            self.initial['repair_type'] = code.repair_type
        if code or (self.instance and self.instance.pk):
            self.fields['product'].disabled = True
            self.fields['repair_type'].disabled = True
        if price_type:
            self.initial['price_type'] = price_type
        if price_type or (self.instance and self.instance.pk):
            self.fields['price_type'].disabled = True

    def clean(self):
        if 'product' in self.cleaned_data and 'price_type' in self.cleaned_data and 'repair_type' in self.cleaned_data:
            if BasePrice.objects.filter(product=self.cleaned_data['product'], price_type=self.cleaned_data['price_type'],
                                        repair_type=self.cleaned_data['repair_type']).exclude(pk=self.instance.pk):
                self.add_error('__all__', 'Для этого прайса и этого вида продукции такой тип ремонта уже задан !')


class IndividualPriceForm(forms.ModelForm):

    class Meta:
        model = CentersPrices
        fields = '__all__'
        widgets = {
            'service_center': forms.Select(attrs={'class': 'form-select'}),
            'product': forms.Select(attrs={'class': 'form-select'}),
            'group': forms.Select(attrs={'class': 'form-select'}),
            'code': forms.Select(attrs={'class': 'form-select'}),
            'price': forms.NumberInput(attrs={'class': 'form-select'}),
        }

    def __init__(self, user=None, code=None, center=None, *args, **kwargs):
        # получение аргументов и содержимого
        super(IndividualPriceForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)

        # установка полей при заданном коде
        if code :
            self.initial['product'] = code.product
            self.initial['group'] = code.parent
            self.initial['code'] = code
        if code or (self.instance and self.instance.pk):
            self.fields['product'].disabled = True
            self.fields['group'].disabled = True
            self.fields['code'].disabled = True

        # определение списка сервисных ценрово в зависимоти от менеджера
        if not user or user.is_superuser or user.groups.filter(name='GeneralStaff').exists():
            self.fields['service_center'].queryset = ServiceCenters.objects.all()
        else:
            self.fields['service_center'].queryset = ServiceCenters.objects.filter(staff_user=user)

        if center:
            self.initial['service_center'] = center
        if center or (self.instance and self.instance.pk):
            self.fields['service_center'].disabled = True

        #это нужно что бы по умолчанию в полях было пусто
        if not code and not instance:
            self.fields['group'].queryset = Codes.objects.none()
            self.fields['code'].queryset = Codes.objects.none()

        # раз по умолчанию в полях пусто - надо создать списки допустимых значений иначе будет ошибка валидации

        have_instruction = False

        if 'product' in self.data and self.data.get('product'):
            have_instruction = True
            try:
                product_id = int(self.data.get('product'))
                self.fields['group'].queryset = Codes.objects.filter(product_id=product_id, is_folder=True, is_active=True).order_by('code')
            except (ValueError, TypeError):
                messages.error(self.request, 'Ошибка получения данных о продукции!')

        if 'group' in self.data and self.data.get('group'):
            have_instruction = True
            try:
                group_id = int(self.data.get('group'))
                self.fields['code'].queryset = Codes.objects.filter(parent_id=group_id, is_folder=False, is_active=True).order_by('code')
            except (ValueError, TypeError):
                messages.error(self.request, 'Ошибка получения данных о группе кодов!')

        if not have_instruction and instance and instance.pk:
            pass

    def clean(self):
        if 'service_center' in self.cleaned_data and 'code' in self.cleaned_data:
            if CentersPrices.objects.filter(service_center=self.cleaned_data['service_center'],
                                                 code=self.cleaned_data['code']).exclude(pk=self.instance.pk):
                self.add_error('__all__', 'Для этого вида продукции такой тип ремонта уже задан !')

