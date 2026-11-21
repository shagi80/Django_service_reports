import datetime
from threading import Thread
from django.utils import timezone
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth import login, logout
from django.views.generic import View, ListView, TemplateView
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from django.db.models import OuterRef, Subquery, Count

from .business_logic import datafile_uploaded, datafile_get_format, STATUS_ACCEPTED, STATUS_PAYMENT, REPORT_STATUS
from reports.models import Reports, ReportsParts
from servicecentres.models import ServiceCenters, ServiceRegions
from reports.forms import ReportTitleForm
from non_repairability_act.models import NonRepairabilityAct, ActStatus, ActStatusHistory
from mail.views import mail_new_acts
from .my_validators import superuser_validation, staff_validation, StaffUserMixin, user_validation
from .forms import *
from .models import ChangeLogs


class HelpPage(TemplateView):
    template_name = 'main/help_page.html'
    

def site_stop(request):
    return render(request, 'main/site_stop.html')


def start_login(request):
    # симуляция выполнения переодических задач 
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.is_staff:
                return redirect('staff_home')
            else:
                try:
                    ServiceCenters.objects.get(user=request.user, is_active=True)
                    return redirect('user_home')
                except Exception:
                    messages.error(request, 'Ошибка привязки логина. Продолжение работы не возможно !')
                    return redirect('login_page')
        else:
            messages.error(request, 'Неверное имя пользовтаеля или пароль')
    else:
        form = UserLoginForm()
    return render(request, 'main/index.html', {'form': form})


#домашняя страница рядового пользователя
@user_passes_test(user_validation)
def user_home(request):
    cont = dict()
    
    # 1. Получаем объект сервисного центра
    senter = get_object_or_404(ServiceCenters, user=request.user)
    
    # 2. Получаем отчеты (QuerySet для отображения)
    # Используем[:3], как в вашем оригинале. 
    # Если нужна пагинация всех отчетов, лимит [:3] нужно будет убрать.
    reports = Reports.objects.filter(service_center=senter).order_by('-id')[:3]
    
    # 3. Ключевой момент для исправления ошибки MySQL 1235:
    # Вычисляем ID отчетов в отдельный список, чтобы избежать LIMIT в подзапросе
    report_ids = list(reports.values_list('id', flat=True))
    
    # 4. Получаем акты
    acts = NonRepairabilityAct.objects.filter(center=senter).order_by('-id')[:3]
    
    # 5. Получаем заказанные детали, используя список ID
    # Фильтруем через report_id__in=report_ids
    ordered_parts = ReportsParts.objects.filter(
        record__report_id__in=report_ids, 
        order_date__isnull=False
    ).exclude(
        record__report__status__in=[STATUS_ACCEPTED, STATUS_PAYMENT]
    ).values('title', 'count')
    
    # 6. Форма и пагинация (исправляем передачу в контекст)
    form = ReportTitleForm()
    
    # Если вы планируете пагинацию, лучше делать её по полному списку отчетов,
    # а не по обрезанному [:3]. Но оставляю структуру как была:
    all_reports = Reports.objects.filter(service_center=senter).order_by('-id')
    paginator = Paginator(all_reports, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 7. Наполнение контекста
    cont['reports'] = reports
    cont['acts'] = acts
    cont['rep_form'] = form
    cont['senter'] = senter
    cont['parts'] = ordered_parts
    cont['page_obj'] = page_obj # Добавляем объект пагинации для шаблона
    
    return render(request, 'main/user_home.html', cont)


#домашяя страница персоланала
@user_passes_test(staff_validation)
def staff_home_1(request):
    cont = {}
    
    # 1. Логи
    cont['staff_actions'] = ChangeLogs.objects.only('pk')[:3]

    # 2. Отчеты
    report_aggregates = Reports.objects.aggregate(
        **{
            f"status_{status_code}": Count('id', filter=Q(status=status_code))
            for status_code, _ in REPORT_STATUS
        }
    )
    
    # Собираем словарь для шаблона
    cont['reports'] = {
        status_code: {
            'title': status_title, 
            'count': report_aggregates.get(f"status_{status_code}", 0)
        } 
        for status_code, status_title in REPORT_STATUS
    }

    # 3. Акты
    # Подзапрос: находит ID САМОЙ ПОСЛЕДНЕЙ записи в истории для конкретного акта
    latest_status_id_subquery = ActStatusHistory.objects.filter(
        act=OuterRef('act')
    ).order_by('-created_at', '-id').values('id')[:1]
    
    # Запрос к истории: берем только те записи, чей ID совпадает с самым свежим ID для их акта
    current_statuses = ActStatusHistory.objects.filter(
        id=Subquery(latest_status_id_subquery)
    )
    
    # Группируем эти уникальные последние записи по полю 'status'
    # .order_by() в конце ОБЯЗАТЕЛЕН — он очищает дефолтную сортировку модели, ломающую GROUP BY!
    act_counts = current_statuses.values('status').annotate(
        total=Count('id')
    ).order_by()
    
    # Превращаем результат в плоский словарь {код_статуса: количество}
    act_counts_dict = {item['status']: item['total'] for item in act_counts}
    
    # Наполняем контекст для шаблона
    cont['acts'] = {
        status.value: {
            'title': status.label, 
            'count': act_counts_dict.get(status.value, 0)
        }
        for status in ActStatus
    }

    # 4. Детали (Оптимизация фильтрации)
    parts_qs = ReportsParts.objects.filter(order_date__isnull=False, send_number__isnull=True)
    
    # Фильтр по регионам (делаем один запрос к ServiceRegions)
    if ServiceRegions.objects.filter(staff_user=request.user).exists():
        parts_qs = parts_qs.filter(
            Q(record__report__service_center__region__staff_user=request.user) |
            Q(record__report__service_center__staff_user=request.user)
        )

    # 5. Просроченные детали — считаем всё одним запросом через Conditional Aggregation
    now = timezone.now()
    expired_aggregates = parts_qs.aggregate(
        p7=Count('id', filter=Q(order_date__lt=now - datetime.timedelta(days=7))),
        p14=Count('id', filter=Q(order_date__lt=now - datetime.timedelta(days=14))),
        p21=Count('id', filter=Q(order_date__lt=now - datetime.timedelta(days=21))),
    )
    cont['expired_parts'] = {k[1:]: v for k, v in expired_aggregates.items() if v > 0}

    # 6. Группировка деталей по сервисным центрам (делаем на стороне БД)
    parts_by_center = parts_qs.values(
        'record__report__service_center__pk', 
        'record__report__service_center__title'
    ).annotate(total_count=Count('id'))

    parts_dict = {}
    for item in parts_by_center:
        pk = item['record__report__service_center__pk']
        if pk:  # Проверка, чтобы PK не был пустым
            parts_dict[pk] = {
                'pk': pk,
                'title': item['record__report__service_center__title'],
                'count': item['total_count']
            }
    
    cont['part_orders'] = parts_dict

    return render(request, 'main/staff_home_1.html', cont)

#выход пользователя
def userlogout(request):
    logout(request)
    return redirect('login_page')


#страница загрузки моделей из файла
@user_passes_test(superuser_validation)
def admin_load_data(request, mod_name):
    cont = {'mod_name': mod_name, 'format_help': datafile_get_format(mod_name)}
    if request.method == 'POST':
        form = DataFileLoadForm(request.POST, request.FILES)
        cont['form'] = form
        if form.is_valid():
            result = datafile_uploaded(request.FILES['file'],mod_name)
            if len(result) != 0:
                msg = 'Ошибки в строках файла: ' +', '.join(result)
                messages.error(request, msg)
            redirect_url = '/admin/' + mod_name.replace('.', '/') + '/'
            return redirect(redirect_url)
    else:
        form = DataFileLoadForm()
        cont['form'] = form
    return render(request, 'main/admin_load_data.html', cont)


#базовый класс для представлений изспользующих формы - позволяет выводить сообщения валидации
class MyFormMessagesView(View):
    success_message = 'my meesage'

    def form_valid(self, form):
        messages.success(self.request, self.success_message)
        return super().form_valid(form)

    def form_invalid(self, form, **kwargs):
        ctx = self.get_context_data(**kwargs)
        text=''
        for error in form.errors:
            text = text + form.errors[error]
        messages.error(self.request, text)
        ctx['form'] = form
        return self.render_to_response(ctx)


class LogsList(LoginRequiredMixin, StaffUserMixin, ListView):
    model = ChangeLogs
    template_name = 'main/logs_list.html'
    context_object_name = 'logs'
    extra_context = {'title': 'Изменения данных'}
    paginate_by = 20

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = LogsFilterForm(self.request.GET)
        context['obj_count'] = self.object_list.count()
        return (context)

    def get_queryset(self):
        logs = ChangeLogs.objects.all()
        if self.request.GET.get("model", '') != '' and self.request.GET.get("model", '') != 'empty':
            logs = logs.filter(model=self.request.GET.get("model"))
        if self.request.GET.get("action_on_model", '') != '' and self.request.GET.get("action_on_model", '') != 'empty':
            logs = logs.filter(action_on_model=self.request.GET.get("action_on_model"))
        if self.request.GET.get("staff_user", '') != '':
            logs = logs.filter(user=self.request.GET.get("staff_user"))
        return logs


class MainPageView(TemplateView):
    template_name = 'main/index1.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = UserLoginForm(self.request.POST)
        return context