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
    reports = Reports.objects.filter(service_center__user=request.user)[:3]
    acts = NonRepairabilityAct.objects.filter(center__user=request.user)[:3]
    senter = get_object_or_404(ServiceCenters, user=request.user)
    ordered_parts = ReportsParts.objects.filter(record__report__in=reports, order_date__isnull=False).\
        exclude(record__report__status__in=[STATUS_ACCEPTED, STATUS_PAYMENT]).values('title', 'count')
    form = ReportTitleForm()
    paginator = Paginator(reports, 10)
    page_number = request.GET.get('page')
    cont['reports'] = reports
    cont['acts'] = acts
    cont['rep_form'] = form
    cont['senter'] = senter
    cont['parts'] = ordered_parts
    return render(request, 'main/user_home.html', cont)


#домашяя страница персоланала
@user_passes_test(staff_validation)
def staff_home_1(request):
    """ главная страницы менеджера  """

    from django.db.models import Q, Count, F

    cont = dict()
    # получение логов изменения данных
    logs = ChangeLogs.objects.all()[:3].values('pk')
    # получение данных по отчетам
    reports_data = {}
    for status in REPORT_STATUS:
        item_data = {}
        item_data['title'] = status[1] 
        item_data['count'] = Reports.objects.filter(status=status[0]).count()
        reports_data[status[0]] = item_data
    # получение данных по актам
    acts_data = {}
    acts = NonRepairabilityAct.objects.all()
    for status in ActStatus:
        item_data = {}
        item_data['title'] = status.label
        id = [act.id for act in acts if act.status.status == status]
        item_data['count'] = len(id)
        acts_data[status] = item_data
    # получение списка заказанных деталей
    parts = ReportsParts.objects.filter(order_date__isnull=False, send_number__isnull=True).\
        annotate(center_title=F('record__report__service_center__title'),\
                 center_pk=F('record__report__service_center__pk')).\
                    values('center_title', 'center_pk', 'order_date')   
    #if not request.user.is_superuser and not request.user.groups.filter(name='GeneralStaff'):
    if ServiceRegions.objects.filter(staff_user=request.user):
        parts = parts.filter(
                Q(order_date__isnull=False)&(
                Q(record__report__service_center__region__staff_user = request.user)|
                Q(record__report__service_center__staff_user = request.user)                
                )
            )
    expired_periods = [7, 14, 21]
    expired_parts = {}
    for period in expired_periods:
        count = parts.filter(
            order_date__lt=(datetime.datetime.now()-datetime.timedelta(days=period))
            ).count()
        if count:
            expired_parts[str(period)] = count
    parts = parts.annotate(count=Count('record__report__service_center__title'))
    parts_dict = {}
    for item in parts:
        if item['center_pk'] in parts_dict:
            parts_dict[item['center_pk']]['count'] += item['count']
        else:
            parts_dict[item['center_pk']] = {'count': item['count'], 'title': item['center_title'], 'pk': item['center_pk'] }

    cont['part_orders'] = parts_dict
    cont['expired_parts'] = expired_parts
    cont['staff_actions'] = logs
    cont['reports'] = reports_data
    cont['acts'] = acts_data
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