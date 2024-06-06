import datetime
from django import template
from django.db.models import Max, Min
from servicecentres.models import *
from ..business_logic import GetPrices
from products.models import *
from ..models import *
from reports.models import ReportsParts

# для использования тэгов в заголовк HTML нужно дабавить {% load my_tags %}


register = template.Library()


# для удаление пробелов и прочего невидимого из якобы пустых строк (в шаблоне списка контактов)
@register.filter
def delspace(value):
    if value:
        res = value.split()
        if len(res) == 0:
            return 0
        else:
            return res
    return None


# для передачи набора фильтров из URL в пагинатор (в шаблоне пагинатора) для страниц с фильтрацией
@register.simple_tag
def get_filters(request):
    res = ''
    for itm in request.GET:
        if itm != 'page':
            res = res + '&' + itm + '=' + request.GET.get(itm)
    return res


@register.inclusion_tag('main/tag_show_code_for_product.html')
def show_code_for_product(user, product=None, center=None):
    from products.models import Codes
    code_list = []
    if product:
        codes = Codes.objects.filter(product=product).order_by('code')
    else:
        codes = Codes.objects.filter(product=product).order_by('-is_folder', 'code')
    user_status = 'user'
    if user.is_staff:
        user_status = 'staff'
        if user.is_superuser or user.groups.filter(name='GeneralStaff').exists():
            user_status = 'general_staff'
    for code in codes:
        val_list = []
        individual_price = None
        if center:
            val_str = None
            val = GetPrices(code, center)
            if val:
                if 'individual_price' in val:
                    individual_price = val['individual_price']
                val_str = str(val['price']) + ' руб'
        else:
            base = BasePrice.objects.filter(product=product, repair_type=code.repair_type)
            base_min = base.aggregate(Min('price'))['price__min']
            if base_min and base_min > 0:
                val_list.append(base_min)
            base_max = base.aggregate(Max('price'))['price__max']
            if base_max and base_max > 0:
                val_list.append(base_max)
            individual = CentersPrices.objects.filter(code=code)
            individual_min = individual.aggregate(Min('price'))['price__min']
            if individual_min and individual_min > 0:
                val_list.append(individual_min)
            individual_max = individual.aggregate(Max('price'))['price__max']
            if individual_max and individual_max > 0:
                val_list.append(individual_max)
            val_str = None
            if val_list:
                min_val = min(val_list)
                max_val = max(val_list)
                val_str = str(min_val)
                if min_val != max_val:
                    val_str = val_str + '-' + str(max_val)
                val_str = val_str + ' руб'
        item = {'code': code, 'prices': val_str, 'individual_price': individual_price}
        code_list.append(item)
    return {'items': code_list, 'user': user_status, 'center': center}


# определение принадлежит ли пользователь определенной группе пользователей
@register.filter(name='has_group')
def has_group(user, group_name):
    return user.groups.filter(name=group_name).exists()


# список продуции для страниц "модели", "коды", "расценки"
@register.inclusion_tag('main/tag_products_list.html')
def show_products_list(products):
    return {'products': products, }


@register.inclusion_tag('main/tag_log_data.html')
def show_log(action_id):
    action = ChangeLogs.objects.get(pk=int(action_id))
    obj_description = []
    try:
        if action.model == MODEL_CODES:
            obj = Codes.objects.get(id=action.record_id)
            if obj.product:
                obj_description.append('Продукция: ' + str(obj.product))
            else:
                obj_description.append('Продукция: общий код')
            obj_description.append('Группа кодов: ' + str(obj.parent))
            obj_description.append('Код: ' + str(obj.code))
        elif action.model == MODEl_PRODUCT:
            obj = MainProducts.objects.get(id=action.record_id)
            obj_description.append('Тип продуции: ' + str(obj))
        elif action.model == MODEL_PODUCT_MODELS:
            obj = Models.objects.get(id=action.record_id)
            obj_description.append('Тип продуции: ' + str(obj.product))
            obj_description.append('Модель: ' + str(obj.title))
        elif action.model == MODE_BASE_PRICE:
            obj = BasePrice.objects.get(id=action.record_id)
            obj_description.append('Тип продуции: ' + str(obj.product))
            obj_description.append('Тип ремоонта: ' + str(obj.get_repair_type_display()))
        elif action.model == MODEL_CENTER_PRICE:
            obj = CentersPrices.objects.get(id=action.record_id)
            obj_description.append('Сервисный центр: ' + str(obj.service_center.title))
            obj_description.append('Тип продукции: ' + str(obj.product))
            obj_description.append('Код дефекта: ' + str(obj.code))
        elif action.model == MODEL_CENTER:
            obj = ServiceCenters.objects.get(id=action.record_id)
            obj_description.append('Сервисный центр: ' + str(obj.title))
        elif action.model == MODEL_CONTACT:
            obj = ServiceContacts.objects.get(id=action.record_id)
            obj_description.append('Сервисный центр: ' + str(obj.service_center))
        elif action.model == MODEL_REGIONS:
            obj = ServiceRegions.objects.get(id=action.record_id)
            obj_description.append('Регион СЦ: ' + str(obj.title))
        else:
            pass
    except Exception:
        pass
    data = {}
    for key in action.data:
        if key != 'ID':
            value = str(action.data[key])
            ind = value.find(':')
            ind += 1
            key = key.replace('title', 'Заголовок')
            key = key.replace('price', 'Расценка')
            if ind > 0:
                val_str = value[ind:-1]
            else:
                val_str = value
            val_str = val_str.replace('True', 'да')
            val_str = val_str.replace('False', 'нет')
            val_str = val_str.replace('very_difficult', 'очень сложный')
            val_str = val_str.replace('difficult', 'сложный')
            val_str = val_str.replace('middle', 'средний')
            val_str = val_str.replace('easy', 'простой')
            val_str = val_str.replace('hard', 'дорогой')
            val_str = val_str.replace('light', 'дешевый')
            data[key] = val_str
    return {'action': action, 'obj_description': obj_description, 'data': data}


@register.inclusion_tag('main/tag_report_header.html')
def show_report_header(report, can_edit, can_delete = False, rep_form=None):
    return {'report': report, 'can_edit': can_edit, 'can_delete': can_delete, 'rep_form': rep_form}


# список деталей в записи о ремоенте для страницы "report_page"
@register.inclusion_tag('main/tag_parts_list.html')
def show_record_parts_list(record):
    parts = ReportsParts.objects.filter(record=record)
    return {'parts': parts, }


# вывод ошибок в виде подсказок в форме добавления записи в отчет
@register.inclusion_tag('main/tag_records_form_fields_errors.html')
def show_record_form_field_errors(errors):
    err_str = ''
    for error in errors:
        err_str = err_str + error + '\n'
    return {'errors': err_str}


@register.filter
def show_verified_proc(report):
    result = report.verified_count / report.records_count * 100 if report.records_count > 0 else 0
    return result


@register.inclusion_tag('main/tag_show_base_price_links.html')
def show_base_price_links():
    from ..business_logic import BASE_PRICE_TYPE
    base_price_type = BASE_PRICE_TYPE
    return {'base_price_type': base_price_type, }


@register.filter
def colored_act_status(status):
    """ Оформление статуса акта цветом. """
    if status:
        if status.status == 'draft':
            return f'<strong class="text-muted">{status.get_status_display()}</strong>'
        elif status.status == 'refinement':
            return f'<strong class="text-danger">{status.get_status_display()}</strong>'
        elif status.status in ['send', 'send_again', 'received']:
            return f'<strong class="text-warning">{status.get_status_display()}</strong>'
        elif status.status == 'accepted':
            return f'<strong class="text-info">{status.get_status_display()}</strong>'
        else:
            return f'<strong class="text-success">{status.get_status_display()}</strong>'
    return None


@register.filter
def translate_nrp_field(field):
    """
    Перевод названия поля из структуры form.errors
    для окна ошибок в Акте неремонтопригодности.
    """
    titles = {
        '__all__': 'Документы:',
        'doc_date': 'Дата документа:',
        'product': 'Тип продукции:',
        'model': 'Модель продукции:',
        'model_description': 'Модель продукции:',
        'serial_number': 'Серийный номер:',
        'problem_description': 'Описание дефекта:',
        'work_type': 'Тип обращения:',
        'client': 'Клиент:',
        'shop': 'Продавец:',
        'receipt_date': 'Даты:',
        'work_description': 'Фактич. неисправность:',
        'decree': 'Заключение:',
        'code': 'Код неисправности'
    }
    return titles[field]


@register.filter
def part_is_expired(date, period):
    """
    Фильтр для определения просроченности детали.
    Дата заказа старше 7 дней.
    """

    last_date = datetime.datetime.now() - datetime.timedelta(days=period)
    return date < last_date.date()


@register.filter
def colored_record_status(status):
    """ Оформление статуса записи цветом. """
    if status:
        if status == 'draft':
            return """<span class="badge rounded-pill bg-secondary">
                черновик
                </span>"""
        elif status == 'order_part':
            return """<span class="badge rounded-pill bg-info">
                детали заказаны
                </span>"""
        elif status == 'part_send_all':
            return """<span class="badge rounded-pill bg-primary">
                все детали в пути
                </span>"""
        elif status == 'part_send_few':
            return """<span class="badge rounded-pill bg-warning">
                детали в пути (частично)
                </span>"""
        elif status == 'work_end':
            return """<span class="badge rounded-pill bg-success">
                ремонт закончен
                </span>"""
        else:
            return None
    return ''


@register.inclusion_tag('main/tag_show_service_member_btn.html')
def show_service_member_btn(center_pk):
    """ Кнопка вызова правой боковой панели. """
    
    member_count = ServiceMember.objects.filter(center__pk=center_pk).count()
    if member_count > 99:
        member_count = '99+'
    return {'center_pk': center_pk, 'member_count': member_count}
