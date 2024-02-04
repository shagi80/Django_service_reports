import datetime
from django import forms
from django.contrib import messages
from django.forms import inlineformset_factory, BaseInlineFormSet
from django.utils.timezone import now
from django.db.models import Q

from reports.models import ReportsRecords, ReportsParts
from products.models import Models, Codes
from main.business_logic import (
    GetPrices,
    MONTH_CHOICES,
    YEAR_CHOICES,
    FACTORY_NOVASIB,
    FACTORY_NOVATEK
    )
from servicecentres.models import ServiceCenters


class ReportTitleForm(forms.Form):
    month = forms.IntegerField(
        initial=now().month,
        widget=forms.Select(
            choices=MONTH_CHOICES,
            attrs={'class': 'form-select form-select-sm'},
        ),
    )
    year = forms.IntegerField(
        initial=now().year,
        widget=forms.Select(
            choices=YEAR_CHOICES, attrs={'class': 'form-select form-select-sm'}
        ),
    )
    note = forms.CharField(
        required=False,
        widget=forms.Textarea(
            attrs={'class': 'form-control form-control-sm', 'rows': 2}
        ),
    )


class RecordForm(forms.ModelForm):
    class Meta:
        model = ReportsRecords
        fields = '__all__'
        widgets = {
            'product': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'model': forms.Select(
                attrs={'class': 'form-select form-select-sm', 'hidden': 'true'}
            ),
            'work_type': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'client_type': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'client': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'client_phone': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'client_addr': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'client_email': forms.EmailInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'model_description': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'serial_number': forms.TextInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'buy_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control-sm',
                    'type': 'date',
                },
            ),
            'start_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control-sm',
                    'type': 'date',
                },
            ),
            'end_date': forms.DateInput(
                format=('%Y-%m-%d'),
                attrs={
                    'class': 'form-control form-control-sm',
                    'type': 'date',
                },
            ),
            'work_cost': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'move_cost': forms.NumberInput(
                attrs={'class': 'form-control form-control-sm'}
            ),
            'problem_description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
            'work_description': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
            'code': forms.Select(
                attrs={'class': 'form-select form-select-sm'}
            ),
            'note': forms.Textarea(
                attrs={'class': 'form-control form-control-sm', 'rows': 2}
            ),
            'total_cost': forms.HiddenInput(),
            'parts_cost': forms.HiddenInput(),
            'report': forms.HiddenInput(),
            'order_part': forms.HiddenInput(),
            # 20.01.2024. Заполенние на основании акта НРП.
            'parent_act': forms.HiddenInput(),
        }

    def __init__(self, report=None, user=None, act=None, *args, **kwargs):

        # получение аргументов и содержимого
        super(RecordForm, self).__init__(*args, **kwargs)
        instance = getattr(self, 'instance', None)
            
        if report:
            self.initial['report'] = report

        if instance.pk and instance.report.pk:
            if (
                (
                    instance.report.status != 'draft'
                    and instance.report.status != 'refinement'
                )
                or (user and user.is_staff and not user.is_superuser)
                or instance.verified
            ):
                for field in self.fields:
                    self.fields[field].disabled = True
            if self.instance.order_parts:
                self.fields['product'].disabled = True
                self.fields['model'].disabled = True
                self.fields['model_description'].disabled = True
                # self.fields['work_type'].disabled = True
                self.fields['serial_number'].disabled = True
                # self.fields['client_type'].disabled = bool(self.instance.client_type)
                # self.fields['client'].disabled = bool(self.instance.client)
                # self.fields['client_phone'].disabled = bool(self.instance.client_phone)
                # self.fields['client_addr'].disabled = bool(self.instance.client_addr)
                # self.fields['client_email'].disabled = bool(self.instance.client_email)
                # self.fields['buy_date'].disabled = (
                #     bool(self.instance.buy_date)
                #     or self.instance.work_type != 'warranty'
                # )
                # self.fields['start_date'].disabled = bool(self.instance.start_date)
                self.fields['order_parts'].disabled = True

        # это нужно что бы по умолчанию в полях было пусто
        self.fields['model'].queryset = Models.objects.none()
        self.fields['code'].queryset = Codes.objects.none()

        # раз по умолчанию в полях пусто - надо создать списки
        # допустимых значений иначе будет ошибка валидации
        if 'product' in self.data and self.data.get('product'):
            try:
                product_id = int(self.data.get('product'))
                self.fields['code'].queryset = Codes.objects.filter(
                    Q(product_id=product_id) | Q(product=None),
                    is_folder=False,
                    is_active=True,
                ).order_by('code')
                self.fields['model'].queryset = Models.objects.filter(
                    product_id=product_id
                ).order_by('title')
            except ():
                messages.error(
                    self.request, 'Ошибка получения данных о продукции!'
                )
        elif instance and instance.pk and self.instance.product:
            try:
                self.fields['code'].queryset = Codes.objects.filter(
                    Q(product=self.instance.product) | Q(product=None),
                    is_folder=False,
                    is_active=True,
                ).order_by('code')
            except ():
                messages.error(
                    self.request, 'Ошибка получения данных о продукции!'
                )
            self.fields['model'].queryset = \
                self.instance.product.parent_product.all()

        # 20.01.2024. Заполнение на основании акта НРП.
        if act:
            self.initial['parent_act'] = act
            self.initial['product'] = act.product
            self.fields['model'].queryset = act.product.parent_product.all()
            self.fields['code'].queryset = Codes.objects.filter(
                    Q(product=act.product) | Q(product=None),
                    is_folder=False,
                    is_active=True,
                ).order_by('code')
            code = Codes.objects.get(code='2')
            if code:
                self.initial['code'] = code
                price_dict = GetPrices(code, report.service_center)
                if 'price' in price_dict:
                    self.initial['work_cost'] = price_dict['price']
            self.initial['model'] = act.model
            self.initial['model_description'] = act.model_description
            self.initial['work_type'] = act.work_type
            self.initial['client_type'] = act.client_type
            if act.client:
                self.initial['client'] = act.client
                self.initial['client_phone'] = act.client_phone
                self.initial['client_addr'] = act.client_addr
            else:
                self.initial['client'] = act.shop
                self.initial['client_phone'] = act.shop_phone
                self.initial['client_addr'] = act.shop_addr
            self.initial['client_email'] = act.client_email
            self.initial['serial_number'] = act.serial_number
            self.initial['buy_date'] = act.buy_date
            self.initial['start_date'] = act.receipt_date
            self.initial['problem_description'] = act.problem_description
            self.initial['work_description'] = (
                act.work_description + ' Решение:' + act.decree
                )

    def clean(self):

        def normalize_string(string):
            sumb_A = ['A', 'А']
            sumb_B = ['B', 'В']
            sumb_C = ['C', 'С']
            sumb_E = ['E', 'Е']
            sumb_H = ['H', 'Н']
            sumb_K = ['K', 'К']
            sumb_P = ['P', 'Р']
            sumb_T = ['T', 'Т']
            sumb_O = ['O', 'О']
            sumb_M = ['M', 'М']
            string = string.upper()
            res = ''
            for sm in string:
                if sm in sumb_A:
                    res = res + 'A'
                elif sm in sumb_B:
                    res = res + 'B'
                elif sm in sumb_C:
                    res = res + 'C'
                elif sm in sumb_E:
                    res = res + 'E'
                elif sm in sumb_H:
                    res = res + 'H'
                elif sm in sumb_K:
                    res = res + 'K'
                elif sm in sumb_P:
                    res = res + 'P'
                elif sm in sumb_T:
                    res = res + 'T'
                elif sm in sumb_O:
                    res = res + 'O'
                elif sm in sumb_M:
                    res = res + 'M'
                else:
                    res = res + sm
            return res

        def clean_client_data(check_email):
            if check_email and (
                'client_email' not in cleaned_data
                or not cleaned_data['client_email']
            ):
                self.add_error(
                    'client_email',
                    [
                        'Это обязательное поле !',
                    ],
                )
            if 'client' not in cleaned_data or not cleaned_data['client']:
                self.add_error(
                    'client',
                    [
                        'Это обязательное поле !',
                    ],
                )
            if (
                'client_phone' not in cleaned_data
                or not cleaned_data['client_phone']
            ):
                self.add_error(
                    'client_phone',
                    [
                        'Это обязательное поле !',
                    ],
                )
            if (
                'client_addr' not in cleaned_data
                or not cleaned_data['client_addr']
            ):
                self.add_error(
                    'client_addr',
                    [
                        'Это обязательное поле !',
                    ],
                )

        NOW_DATE = datetime.datetime.now().date()
        cleaned_data = super().clean()

        if 'move_cost' not in cleaned_data or not cleaned_data['move_cost']:
            self.cleaned_data['move_cost'] = 0
        if 'model' in cleaned_data and cleaned_data['model']:
            self.cleaned_data['model_description'] = str(cleaned_data['model'])
        if 'model_description' in cleaned_data:
            self.cleaned_data['model_description'] = normalize_string(
                cleaned_data['model_description']
            )
        
        # проверка указания модели
        if (
            'model_description' not in cleaned_data
            or not cleaned_data['model_description']
        ):
            self.add_error(
                'model_description',
                [
                    'Обязательное поле !',
                ],
            )
        
        # проверка серийного номера
        if 'serial_number' in cleaned_data:
            self.cleaned_data['serial_number'] = normalize_string(
                cleaned_data['serial_number']
            )
        if 'serial_number' in cleaned_data and 'product' in cleaned_data:
            product = cleaned_data['product']
            serial = cleaned_data['serial_number']
            error = []
            if product.check_serial:
                if not serial[0] in [FACTORY_NOVATEK, FACTORY_NOVASIB]:
                    error.append(
                        'Первый символ кода не соответствует кодировке\
                              производителя !'
                    )
                else:
                    self.cleaned_data['factory'] = serial[0]
                    if 'model' in cleaned_data and cleaned_data['model']:
                        model = cleaned_data['model']
                        first_char = serial.find(model.code_chars)
                        if first_char != 1:
                            error.append(
                                'Серийный номер не соответствует модели !'
                            )
                        else:
                            date_str = serial[
                                len(model.code_chars)
                                + 1: len(model.code_chars)
                                + 7
                            ]
                            try:
                                date = datetime.datetime.strptime(
                                    date_str, '%d%m%y'
                                ).date()
                                self.cleaned_data['main_date'] = date
                                if len(serial) != len(model.code_chars) + 11:
                                    error.append(
                                        'Длинна серийного номера меньше\
                                              необходимой !'
                                    )
                                else:
                                    if serial[
                                        len(model.code_chars) + 7
                                    ] not in ('A', 'B', 'C', 'D', 'E', 'F'):
                                        error.append(
                                            'Невозможно определить код смены !'
                                        )
                                    else:
                                        self.cleaned_data['shift'] = serial[
                                            len(model.code_chars) + 7
                                        ]
                                        num = serial[
                                            len(model.code_chars) + 8:
                                        ]
                                        if not num.isdigit():
                                            error.append(
                                                'Невозможно определить\
                                                      порядковый номер изделий !'
                                            )
                                        else:
                                            pass
                            except ValueError:
                                error.append(
                                    'Невозможно определить дату производства !'
                                )
            if error:
                self.add_error('serial_number', error)
        
        # проверка даты поупки
        if (
            'work_type' in cleaned_data
            and cleaned_data['work_type'] == 'warranty'
            and not cleaned_data['buy_date']
            ):
            self.add_error('buy_date', 'Обязательное поле !')
        if 'buy_date' in cleaned_data and cleaned_data['buy_date']:
            buy_date = cleaned_data['buy_date']
            if (
                'start_date' in cleaned_data
                and cleaned_data['start_date']
                and buy_date > cleaned_data['start_date']
                ):
                self.add_error(
                    'buy_date',
                    'Дата покупки позднее даты начала ремонта !',
                )
            if (
                'end_date' in cleaned_data
                and cleaned_data['end_date']
                and buy_date > cleaned_data['end_date']
                ):
                self.add_error(
                    'buy_date',
                    'Дата покупки позднее даты окончания ремонта !',
                )
            if buy_date > NOW_DATE:
                self.add_error(
                    'buy_date', 'Дата покупки товара в будущем !'
                )
        
        # проыерка даты начала ремонта
        if ('start_date' in cleaned_data and cleaned_data['start_date']):
            start_date = cleaned_data['start_date']
            if start_date > NOW_DATE:
                self.add_error('start_date', 'Дата начала ремонта в будущем !')
            if (
                'end_date' in cleaned_data
                and cleaned_data['end_date']
                and start_date > cleaned_data['end_date']
                ):
                self.add_error(
                    'start_date',
                    'Дата начала ремонта позднее даты окончания !',
                )
        
        # проверка даты окончания ремонта
        if ('end_date' in cleaned_data and cleaned_data['end_date']):
            end_date = cleaned_data['end_date']
            if end_date > NOW_DATE:
                self.add_error(
                    'end_date', 'Дата окончания ремонта в будущем !'
                )

        # проверка типа продукции и запрос e-mail организаций
        if (
            'work_type' in cleaned_data
            and cleaned_data['work_type'] == 'warranty'
            and not cleaned_data['client_type']
            ):
            self.add_error(
                'client_type',
                [
                    'Это обязательное поле !',
                ],
            )
        if 'client_type' in cleaned_data and cleaned_data['client_type']:
            if cleaned_data['client_type'] == 'organization':
                clean_client_data(True)
            else:
                if (
                    'work_type' in cleaned_data
                    and cleaned_data['work_type'] == 'warranty'
                ):
                    clean_client_data(False)
                else:
                    self.add_error(
                        'client_type',
                        [
                            'Предторгвое изделие не может принадлежать физлицу !',
                        ],
                    )

        # проверка на не критичные ошибки
        warnings = ''
        # соответствмие цены
        if (
            'code' in cleaned_data
            and 'report' in cleaned_data
            and 'work_cost' in cleaned_data
        ):
            code = cleaned_data['code']
            report = cleaned_data['report']
            price_dict = GetPrices(code, report.service_center)
            if 'price' in price_dict:
                if int(price_dict['price']) != int(cleaned_data['work_cost']):
                    warnings = (
                        warnings + 'Стоимость работ не соотвествует прайсу; '
                    )
        # длительность гарантийного срока
        if (
            'buy_date' in cleaned_data
            and cleaned_data['buy_date']
            and 'start_date' in cleaned_data
            and cleaned_data['start_date']
            and 'product' in cleaned_data
            and cleaned_data['product']
        ):
            guarantee_period = cleaned_data['product'].guarantee_period * 365
            if (
                cleaned_data['start_date'] - cleaned_data['buy_date']
            ).days > guarantee_period:
                warnings = warnings + 'Гарантийный срок истек; '
        # прверка многократности ремонта
        if 'serial_number' in cleaned_data and 'product' in cleaned_data:
            records = ReportsRecords.objects.filter(
                product=cleaned_data['product'],
                serial_number=cleaned_data['serial_number'],
            ).exclude(pk=self.instance.pk)
            if records:
                if records.filter(
                    report__service_center=cleaned_data[
                        'report'
                    ].service_center
                ):
                    message = 'Изделие с этим серийным номером уже было в ремонте в этом СЦ'
                else:
                    message = 'Изделие с этим серийным номером уже было в ремонте в другом СЦ'
                if records.filter(report=cleaned_data['report']):
                    message = (
                        'Этот серийный номер уже был указан в этом отчете'
                    )
                warnings = warnings + message + '; '
        if warnings:
            warnings = warnings[:-2]
            cleaned_data['errors'] = warnings
        else:
            cleaned_data['errors'] = None


class PartsInlineFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields['ORDERED'] = forms.BooleanField(required=False)

    def __init__(self, *args, user=None, **kwargs):

        super(PartsInlineFormSet, self).__init__(*args, **kwargs)
        if (
            self.instance.pk
            and self.instance.report
            and self.instance.report.pk
        ):
            if (
                (
                    self.instance.report.status != 'draft'
                    and self.instance.report.status != 'refinement'
                )
                or (user and user.is_staff and not user.is_superuser)
                or self.instance.verified
            ):
                for form in self.forms:
                    for field in form.fields:
                        form.fields[field].disabled = True

    def clean(self):
        super().clean()
        for form in self.forms:
            if 'title' in form.cleaned_data:
                record = form.cleaned_data['record']
                if (
                    (form.cleaned_data['document'] is None)
                    and (form.cleaned_data['order_date'] is None)
                    and (not form.cleaned_data['ORDERED'])
                ):
                    form.add_error('document', 'Обязательное поле')
                if (
                    (not form.cleaned_data['price'])
                    and (form.cleaned_data['order_date'] is None)
                    and (not form.cleaned_data['ORDERED'])
                    and (not record.report.service_center.free_parts)
                ):
                    form.add_error('price', 'Обязательное поле')


PartsFormset = inlineformset_factory(
    ReportsRecords,
    ReportsParts,
    extra=1,
    formset=PartsInlineFormSet,
    fields='__all__',
    absolute_max=10,
    max_num=10,
    widgets={
        'title': forms.TextInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
        'count': forms.NumberInput(
            attrs={'class': 'form-control form-control-sm', 'data-counter': ''}
        ),
        'price': forms.NumberInput(
            attrs={'class': 'form-control form-control-sm', 'data-counter': ''}
        ),
        'document': forms.TextInput(
            attrs={'class': 'form-control form-control-sm'}
        ),
        'order_date': forms.DateInput(
            attrs={
                'class': 'form-control form-control-sm disabled',
            }
        ),
    },
)


class ReportsFilterForm(forms.Form):
    from servicecentres.models import ServiceCenters
    from django.contrib.auth.models import User
    from main.business_logic import REPORT_STATUS

    SEVICE_CHOICES = tuple(
        ServiceCenters.objects.all().values_list('pk', 'title')
    )

    service_center = forms.IntegerField(
        required=False,
        widget=forms.Select(
            choices=(('', 'все сервисы ...'),) + SEVICE_CHOICES,
            attrs={'class': 'form-select form-select-sm'},
        ),
    )
    month = forms.IntegerField(
        initial=now().month,
        required=False,
        widget=forms.Select(
            choices=(('', '...'),) + MONTH_CHOICES,
            attrs={'class': 'form-select form-select-sm'},
        ),
    )
    year = forms.IntegerField(
        initial=now().year,
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
        choices=(('', 'все статусы ...'),) + REPORT_STATUS,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    staff_user = forms.ModelChoiceField(
        queryset=User.objects.filter(is_staff=True),
        empty_label='все менеджеры ...',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )


class UserPartForm(forms.Form):
    """фильтр на странице Заказанные детали"""

    # преобразование qset в choices для уменьшения количества запросов
    centers = [
        (itm['id'], itm['title'])
        for itm in ServiceCenters.objects.all()
        .exclude(is_active=False)
        .values('id', 'title')
        .distinct()
    ]
    blank = [
        ('', 'Все сервисные центры ....'),
    ]

    filter = forms.CharField(
        required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    center = forms.ChoiceField(
        choices=blank + centers,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select form-select-sm'}),
    )
    period = forms.ImageField(
        required=False, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )
    show_send = forms.BooleanField(
        label='активные',
        required=False,
        widget=forms.CheckboxInput(
            attrs={'type': 'checkbox', 'class': 'form-check-input'}
        ),
    )
    send_start = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'class': 'form-control form-control-sm','type': 'date'})
    )
    send_end = forms.DateField(
        required=False, widget=forms.DateInput(attrs={'class': 'form-control form-control-sm', 'type': 'date'})
    )