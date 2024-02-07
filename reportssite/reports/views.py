import re
import datetime
import calendar
from django.utils.encoding import escape_uri_path
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpResponseForbidden,
    HttpResponseRedirect,
    HttpResponse,
    HttpResponseNotFound,
    Http404,
)
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import (
    CreateView,
    UpdateView,
    DetailView,
    ListView,
    TemplateView,
)
from django.utils.http import url_has_allowed_host_and_scheme
from django.db.models import Q
from django.core.mail import send_mail

from main.my_validators import *
from .forms import *
from .models import *
from servicecentres.models import ServiceCenters, ServiceRegions
import xlwt
from upload.forms import ReportDocumentForm, RecordDocumentForm
from mail.views import (
    mail_ordered_parts,
    mail_send_parts,
    mail_message_for_center,
)

from main.business_logic import GetPrices, STATUS_ACCEPTED, STATUS_PAYMENT
from reportssite.settings import DEBUG
from non_repairability_act.models import NonRepairabilityAct, ActStatus
from reports.export import order_part_blank, report_xls, part_order_xls, part_order_list_xls


# -------------------------- ОТПРАКА ПОЧТЫ -------------------------------

# отправка письма пользователю об изменении статуса отчета
def SendReportSatus(email, report, note):
    """отправка электронного письма польхователю"""

    msg = f'Статус вашего отчета за {report.get_report_month()} изменен на\
          "{report.get_status_display()}"\n\n'
    if note:
        msg = msg + 'Сообщение от менедежера:\n'
        msg = msg + note + '\n\n'
    msg = (
        msg
        + 'Это письмо сформированно автоматическа, отвечать на него не нужно.'
    )
    send_mail(
        'RENOVA. Статус вашего отчета изменен',
        msg,
        'report_service@re-nova.com',
        ['shagi80@mail.ru'] if DEBUG else [email],
        fail_silently=False,
    )


# отправка письма менеджеру о поступлении отчета
def SendReportToStaff(report):
    """отправка электронного письма менеджеру"""
    email = report.service_center.staff_user.email
    if email:
        msg = f'Получен отчет от {report.service_center}\
              за {report.get_report_month()}.\n\n'
        msg = (
            msg
            + 'Это письмо сформированно автоматическа,\
                  отвечать на него не нужно.'
        )
        send_mail(
            f'RENOVA. Получен отчет {report} ({report.get_status_display()})',
            msg,
            'report_service@re-nova.com',
            ['shagi80@mail.ru'] if DEBUG else [email],
            fail_silently=False,
        )


# ------------------------- РАБОТА С ОТЧЕТОМ ДЛЯ USERA ----------------------

# показ списка отчетоd полбзователю
class ReportsForUser(
LoginRequiredMixin, UserMixin, ListView):
    model = Reports
    template_name = 'reports/reports_list.html'
    context_object_name = 'reports'
    extra_context = {'title': 'Все отчеты:'}
    paginate_by = 10

    def get_queryset(self):
        reports = Reports.objects.filter(
            service_center=self.request.user.service_center()
        )
        if (
            'status' in self.request.GET
            and self.request.GET.get('status', '') != ''
        ):
            reports = reports.filter(status=self.request.GET.get('status'))
        if (
            'year' in self.request.GET
            and 'month' in self.request.GET
            and self.request.GET.get('year', '') != ''
            and self.request.GET.get('month', '') != ''
        ):
            report_date = datetime.date(
                int(self.request.GET.get('year', '')),
                int(self.request.GET.get('month', '')),
                1,
            )
            reports = reports.filter(report_date=report_date)
        return reports

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ReportsFilterForm(self.request.GET)
        context['obj_count'] = self.object_list.count()
        return context


# экспорт отчета в эксель
@user_passes_test(user_validation)
def export_report_xls(request, report_pk):
    report = get_object_or_404(Reports, pk=report_pk)
    response = HttpResponse(content_type='application/ms-excel')
    disp = (
        'attachment; filename="Report of '
        + report.report_date.strftime('%b %Y')
        + ' .xls"'
    )
    response['Content-Disposition'] = disp
    workBook = report_xls(report)
    workBook.save(response)
    return response


# добавление отчета
@user_passes_test(user_validation)
def ReportAdd(request):
    if request.method == 'POST':
        form = ReportTitleForm(request.POST)
        if form.is_valid():
            report_date = datetime.date(
                form.cleaned_data['year'], form.cleaned_data['month'], 1
            )
            note = form.cleaned_data['note']
            user = request.user
            try:
                center = ServiceCenters.objects.get(user=user, is_active=True)
            except ():
                messages.error(
                    request,
                    'Ощибка при добавлении отчета: сервисный центр\
                          не найден !',
                )
                return redirect('user_home')
            if Reports.objects.filter(
                report_date=report_date, service_center=center
            ):
                messages.error(
                    request, 'Отчет для этого периода уже существует !'
                )
                return redirect('user_home')
            else:
                report = Reports(
                    service_center=center,
                    user=user,
                    report_date=report_date,
                    note=note,
                )
                report.save()
                return redirect('user_home')
    else:
        return redirect('user_home')


# изменение отчета
@user_passes_test(user_validation)
def ReportUpdate(request, report_pk):
    if request.method == 'POST':
        form = ReportTitleForm(request.POST)
        if form.is_valid():
            report = get_object_or_404(Reports, pk=report_pk)
            if (
                report.service_center.user == request.user
                or request.user.is_superuser
            ):
                report_date = datetime.date(
                    form.cleaned_data['year'], form.cleaned_data['month'], 1
                )
                note = form.cleaned_data['note']
                if Reports.objects.filter(
                    report_date=report_date,
                    service_center=report.service_center,
                ).exclude(pk=report_pk):
                    messages.error(
                        request, 'Отчет для этого периода уже существует !'
                    )
                    return redirect('report_page', report_pk)
                else:
                    report.report_date = report_date
                    report.note = note
                    report.save()
                    return redirect('report_page', report_pk)
    else:
        return redirect('report_page', report_pk)


# отправка отчета на проверку
@user_passes_test(user_validation)
def ReportSend(request):
    if request.method == 'POST':
        if 'send' in request.POST:
            report_id = request.POST.get('send')
            if report_id:
                report = get_object_or_404(Reports, pk=int(report_id))
                if (
                    report.service_center.user == request.user
                    or request.user.is_superuser
                ):
                    report.status = (
                        'send_again'
                        if report.status == 'refinement'
                        else 'send'
                    )
                    report.send_date = datetime.datetime.now().date()
                    report.save()
                    SendReportToStaff(report)
    return redirect('user_home')


# прверка возможности отправки отчета на проверку
@user_passes_test(user_validation)
def ReportCanSend(request):
    if 'report' in request.GET and request.GET.get('report'):
        report = get_object_or_404(Reports, pk=int(request.GET.get('report')))
        records = report.reportsrecords_set.filter(
            end_date__isnull=True
        ).count()
        if records:
            return HttpResponse('can_not')
        else:
            return HttpResponse('can')
    return Http404()


# AJAX выдача списка подтвержденных актов НРП
class GetNonRepairabilityAct(LoginRequiredMixin, UserMixin, View):
    def get(self, request):        
        acts = NonRepairabilityAct.objects.filter(
            center=request.user.service_center(),
            child_record__isnull=True
            )
        id = [
                act.id
                for act in acts
                if (
                    act.status.status == ActStatus.COMPENSATED
                    or act.status.status == ActStatus.CONFIRMED
                    )
            ]
        acts = acts.filter(id__in=id).values(
                'pk',
                'doc_date',
                'product__title',
                'model_description',
                'serial_number',
                'client',
                'shop'
            )
        context = {}
        context['acts'] = acts
        context['reportPk'] = request.GET['report_pk']
        return render(request, 'reports/get_acts.html', context)


# ------------------------- РАБОТА С ОТЧЕТОМ ДЛЯ ЮЗЕРА И МЕНЕДЖЕРА -----------------------------


class ReportDetail(LoginRequiredMixin, UserMixin, DetailView):
    model = Reports
    template_name = 'reports/report_page.html'
    context_object_name = 'report'
    extra_context = {'title': 'Отчет за '}
    previos_url = None

    def dispatch(self, request, *args, **kwargs):
        if 'previos' in self.request.GET:
            self.previos_url = self.request.get_full_path().split('previos')[
                1
            ][1:]
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        report = self.get_object()
        return (
            report.service_center.user == self.request.user
            or self.request.user.is_staff
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = ReportTitleForm()
        form.initial['month'] = self.object.report_date.month
        form.initial['year'] = self.object.report_date.year
        form.initial['note'] = self.object.note
        records = ReportsRecords.objects.filter(report=self.object)
        context['records'] = records
        context['can_delete'] = (
            self.object.service_center.user == self.request.user
        ) and (
            (not records.filter(order_parts=True))
            or (self.request.user.is_superuser)
            or (not records)
        )
        context['rep_form'] = form
        context['previos_url'] = self.previos_url
        context['document_form'] = ReportDocumentForm({'report': self.object})
        return context


# ------------------ РАБОТА С ОТЧЕТОМ ДЛЯ МЕНЕДЖЕРА ----------------------

# изменение статуса отчета
@user_passes_test(staff_validation)
def ReportChangeStatus(request):
    from main.business_logic import REPORT_STATUS

    if request.method == 'POST':
        new_status = None
        report_id = None
        mail_note = ''
        if 'send_refinement' in request.POST:
            report_id = request.POST.get('send_refinement')
            new_status = 'refinement'
            mail_note = request.POST.get('message')
        else:
            for status in REPORT_STATUS:
                if status[0] in request.POST:
                    report_id = request.POST.get(status[0])
                    if status[0] == 'draft':
                        new_status = 'send'
                    elif status[0] == 'send' or status[0] == 'send_again':
                        new_status = 'received'
                    elif status[0] == 'received':
                        new_status = 'verified'
                    elif status[0] == 'refinement':
                        new_status = 'send_again'
                    elif status[0] == 'verified':
                        new_status = 'accepted'
                    elif status[0] == 'accepted':
                        new_status = 'payment'
                    elif status[0] == 'payment':
                        new_status = 'draft'
        if new_status and report_id:
            report = get_object_or_404(Reports, pk=int(report_id))
            if (
                report.service_center.staff_user == request.user
                or request.user.is_superuser
                or request.user.groups.filter(name='GeneralStaff').exists()
            ):
                report.status = new_status
                report.save()
                email = report.service_center.user.email
                if email:
                    SendReportSatus(email, report, mail_note)
                if new_status == 'received':
                    return redirect('report_page', report.pk)
    next = request.META.get('HTTP_REFERER')
    if url_has_allowed_host_and_scheme(next, request.get_host()):
        return redirect(next)
    return redirect('reports_list')


# показ списка отчетов менеджеру
class ReportsForStaff(LoginRequiredMixin, StaffUserMixin, ListView):
    model = Reports
    template_name = 'reports/reports_list.html'
    context_object_name = 'reports'
    extra_context = {'title': 'Все отчеты:'}
    paginate_by = 10

    def get_queryset(self):
        if self.request.user.is_superuser:
            reports = Reports.objects.all()
        elif self.request.user.is_staff:
            reports = Reports.objects.all().exclude(status='draft')
        if self.request.GET.get('service_center', '') != '':
            reports = reports.filter(
                service_center=self.request.GET.get('service_center')
            )
        if self.request.GET.get('staff_user', '') != '':
            reports = reports.filter(
                service_center__staff_user=self.request.GET.get('staff_user')
            )
        if (
            'status' in self.request.GET
            and self.request.GET.get('status', '') != ''
        ):
            reports = reports.filter(status=self.request.GET.get('status'))
            if (
                self.request.GET.get('status') == 'send'
                or self.request.GET.get('status') == 'send_again'
            ):
                reports = reports.order_by('-send_date')
        if (
            'year' in self.request.GET
            and 'month' in self.request.GET
            and self.request.GET.get('year', '') != ''
            and self.request.GET.get('month', '') != ''
        ):
            report_date = datetime.date(
                int(self.request.GET.get('year', '')),
                int(self.request.GET.get('month', '')),
                1,
            )
            reports = reports.filter(report_date=report_date)
        return reports

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = ReportsFilterForm(self.request.GET)
        context['obj_count'] = self.object_list.count()
        return context


# ------------------- РАЬОТА С ЗАПИСЬЮ О РЕМОНТЕ ДЛЯ USERA -------------------------

# копирование записи о ремонте
@user_passes_test(user_validation)
def RecordCopy(request):
    """копирование записи"""
    if request.method == 'POST':
        if 'copy' in request.POST:
            record_id = request.POST.get('copy')
            if record_id:
                new_record = get_object_or_404(
                    ReportsRecords, pk=int(record_id)
                )
                new_record.pk = None
                new_record.serial_number = ''
                new_record.order_parts = False
                new_record.save()
                return redirect('record_update_page', new_record.pk)
    return HttpResponseNotFound()


# перенос записи на следующий месяц
@user_passes_test(user_validation)
def RecordRemove(request):
    """перенос записи на следующий месяц"""
    if request.method == 'POST':
        if 'remove' in request.POST:
            record_id = request.POST.get('remove')
            if record_id:
                record = get_object_or_404(ReportsRecords, pk=int(record_id))
                # вычисляем дату отчета для следующего месяца
                days = calendar.monthrange(
                    record.report.report_date.year,
                    record.report.report_date.month,
                )[1]
                next_month_date = (
                    record.report.report_date + datetime.timedelta(days=days)
                )
                # пытаемся найти уже сущетвующие отчеты за следующий месяц
                reports = Reports.objects.filter(
                    service_center=record.report.service_center,
                    report_date=next_month_date,
                )
                if reports:
                    # отчет должен быть один
                    if reports.count() > 1:
                        raise Http404('Целевых отчетов больше чем один !')
                    # отчет должен быть черновиком или на доработке
                    if not reports.first().status in ['draft', 'refinement']:
                        messages.error(
                            request,
                            'Отчет за следующий месяц уже отправлен на проверку !',
                        )
                        return redirect('report-update', record.report.pk)
                    new_report = reports.first()
                else:
                    # если отчета не существует создаеи его
                    new_report = Reports.objects.create(
                        service_center=record.report.service_center,
                        report_date=next_month_date,
                        user=record.report.user,
                    )
                # переподчиняем запись
                old_report = record.report
                record.report = new_report
                record.save()
                old_report.save()   # мы должны пересохранить старый отчет что бы обновить итоги
                messages.success(
                    request,
                    f'Запись успешно перенесена в отчет за {new_report.get_report_month()} !',
                )
                return redirect('report-update', new_report.pk)
    return HttpResponseNotFound()


# общие процеудуры представлений добавления и обновления записи
class RecordView(View):
    success_message = 'my meesage'
    form_class = RecordForm
    error_message = 'Пожалуйста, проверьте форму !'
    template_name = 'reports/records_add.html'
    report = None

    def test_func(self):
        if self.object:
            report = self.object
        else:
            report = get_object_or_404(Reports, pk=self.kwargs['report_pk'])
        return (
            report.service_center.user == self.request.user
            or self.request.user.is_superuser
            or (
                report.status != 'draft'
                and (
                    self.request.user.groups.filter(
                        name='GeneralStaff'
                    ).exists()
                    or report.service_center.staff_user == self.request.user
                )
            )
        )

    def form_invalid(self, form, **kwargs):
        ctx = self.get_context_data(**kwargs)
        parts_formset = PartsFormset(
            form.data, instance=form.instance, prefix='parts_formset'
        )
        ctx['form'] = form
        ctx['parts_formset'] = parts_formset
        if 'errors' not in form.errors:
            # messages.error(self.request, form.errors)
            messages.error(self.request, self.error_message)
        return render(self.request, self.template_name, ctx)

    def form_valid(self, form):
        # if not form.instance.pk:
        #   form.save()
        parts_formset = PartsFormset(
            form.data, instance=form.instance, prefix='parts_formset'
        )
        if parts_formset.is_valid():
            # сохраняем как есть по соответствующей кнопке или проверяем некритичные ошибки
            if (
                form.cleaned_data['errors']
                and 'save_with_warning' not in self.request.POST
            ):
                errors_list = form.cleaned_data['errors'].split(';')
                form.add_error('errors', errors_list)
                return self.form_invalid(form)
            else:
                # только этот кусок кода выполняется если все хорошо и можно записывать
                messages.success(self.request, self.success_message)
                form.save()
                parts_formset.save()
                # проверяем список деталей на предмет заказа
                ordered_parts = []
                for part_form in parts_formset.forms:
                    if (
                        'ORDERED' in part_form.cleaned_data
                        and part_form.cleaned_data['ORDERED']
                    ):
                        part_form.instance.order_date = datetime.datetime.now()
                        part_form.instance.price = 0
                        part_form.instance.save()
                        part = {
                            'title': part_form.instance.title,
                            'count': part_form.instance.count,
                        }
                        ordered_parts.append(part)
                if ordered_parts:
                    if mail_ordered_parts(form.instance, ordered_parts):
                        messages.info(
                            self.request, 'Заказ на детали отправлен !'
                        )
                    else:
                        messages.error(
                            self.request,
                            'Ошибка при отравке заказа на запчасти !',
                        )
                    if not form.instance.order_parts:
                        form.instance.order_parts = True
                        form.instance.save()
                # завершение работы view
                return HttpResponseRedirect(self.get_success_url())
        else:
            form.is_valid = False
            errors = []
            for form_error in parts_formset.errors:
                if form_error:
                    for key in form_error:
                        err_string = key + ' ' + form_error[key].as_text()
                        err_string = err_string.replace(
                            'title', 'Наименование'
                        )
                        err_string = err_string.replace('count', 'Количество')
                        err_string = err_string.replace('document', 'Документ')
                        err_string = err_string.replace('price', 'Цена')
                        err_string = err_string.replace('*', '-')
                        errors.append(err_string)
            form.add_error('parts_cost', errors)
            return self.form_invalid(form)

    def get_success_url(self):
        if (
            'continue' in self.request.POST
            or 'save_with_warning' in self.request.POST
        ):
            return self.request.path_info
        if 'close' in self.request.POST:
            if self.object:
                return reverse(
                    'report-update',
                    kwargs={'report_pk': self.object.report.pk},
                )
            return reverse(
                'report-update', kwargs={'report_pk': self.kwargs['report_pk']}
            )


class RecordAdd(LoginRequiredMixin, RecordView, CreateView):
    success_message = 'Ремонт успешно добавлен !'
    extra_context = {'title': 'Добавление ремонта в отчет за '}

    def setup(self, request, *args, **kwargs):
        super(RecordAdd, self).setup(request, *args, **kwargs)
        self.report = get_object_or_404(Reports, pk=self.kwargs['report_pk'])

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['report'] = self.report
        if 'act_pk' in self.kwargs:
            act = get_object_or_404(
                NonRepairabilityAct,
                pk=self.kwargs['act_pk']
                )
            if act.center != self.request.user.service_center():
                raise Http404
            kwargs['act'] = act
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = get_object_or_404(
            Reports, pk=self.kwargs['report_pk']
        )
        context['can_edit'] = True
        context['parts_formset'] = PartsFormset(
            instance=self.object,
            prefix='parts_formset',
            user=self.request.user,
        )
        return context


class RecordUpdate(LoginRequiredMixin, RecordView, UpdateView):
    model = ReportsRecords
    extra_context = {'title': 'Ремонт из отчета  '}
    success_message = 'Ремонт успешно изменен !'

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['user'] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['report'] = self.object.report
        context['record'] = self.object
        context['can_edit'] = (
            (
                self.object.report.status == 'draft'
                or self.object.report.status == 'refinement'
            )
            and (
                not self.request.user.is_staff
                or self.request.user.is_superuser
            )
            and not self.object.verified
        )
        context['parts_formset'] = PartsFormset(
            instance=self.object,
            prefix='parts_formset',
            user=self.request.user,
        )
        context['document_form'] = RecordDocumentForm({'record': self.object})
        return context


# ------------------- РАЬОТА С ЗАПИСЬЮ О РЕМОНТЕ ДЛЯ МЕНЕДЖЕРА -------------------------

# страница ремонта для менеджера
class RecordForStaff(LoginRequiredMixin, StaffUserMixin, DetailView):
    model = ReportsRecords
    context_object_name = 'record'
    template_name = 'reports/record_for_staff.html'
    extra_context = {'close_status': ['refinement', 'send', 'send_again']}


# замечание менеджера к отчету
@user_passes_test(staff_validation)
def AddRecordMember(request):

    if (
        request.method == 'POST'
        and 'pk' in request.POST
        and request.POST.get('pk')
    ):
        record = get_object_or_404(
            ReportsRecords, pk=int(request.POST.get('pk'))
        )
        if 'text' in request.POST and request.POST.get('text'):
            member = RecordMembers.objects.create(
                record=record,
                author=request.user,
                text=request.POST.get('text'),
            )
            if request.POST.get('mode') != 'for_staff':
                member.for_user = True
                record.remarks = request.POST.get('text')
                record.save()
            member.save()
        return redirect('record-for-staff', pk=record.pk)
    return HttpResponseNotFound()


@user_passes_test(staff_validation)
def DeleteRecordMember(request):

    if (
        request.method == 'POST'
        and 'pk' in request.POST
        and request.POST.get('pk')
    ):
        member = get_object_or_404(
            RecordMembers, pk=int(request.POST.get('pk'))
        )
        record_pk = member.record.pk
        member.delete()
        return redirect('record-for-staff', pk=record_pk)
    return HttpResponseNotFound()


@user_passes_test(staff_validation)
def DeleteRecordRemark(request):

    if (
        request.method == 'POST'
        and 'pk' in request.POST
        and request.POST.get('pk')
    ):
        record = get_object_or_404(
            ReportsRecords, pk=int(request.POST.get('pk'))
        )
        record.remarks = None
        record.save()
        return redirect('record-for-staff', pk=record.pk)
    return HttpResponseNotFound()


# установка флага "ремонт проверен"
@user_passes_test(staff_validation)
def RecordVerified(request):
    from datetime import datetime

    if request.method == 'POST':
        if 'save' in request.POST:
            record_id = request.POST.get('save')
            if record_id:
                record = get_object_or_404(ReportsRecords, pk=int(record_id))
                record.remarks = None
                record.verified = True
                record.verified_date = datetime.now().date()
                record.save()
                return redirect('record-for-staff', record.pk)
    return redirect('user_home')


# снятие флага "ремонт проверен"
@user_passes_test(staff_validation)
def RecordCancelVerified(request):

    if request.method == 'POST':
        if 'save' in request.POST:
            record_id = request.POST.get('save')
            if record_id:
                record = get_object_or_404(ReportsRecords, pk=int(record_id))
                record.verified = False
                record.verified_date = None
                record.save()
                return redirect('record-for-staff', record.pk)
    return redirect('user_home')


# удаление записи о ремонте
@user_passes_test(staff_validation)
def RecordDeleteStaff(request):

    if request.method == 'POST':
        if 'delete' in request.POST:
            record_pk = request.POST.get('delete')
            if record_pk:
                record = get_object_or_404(ReportsRecords, pk=int(record_pk))
                report_pk = record.report.pk
                record.delete()
                subject = 'Один из ваших ремонтов удален менеджером.'
                title = f'Удален ремонт изделия {record.model_description if record.model_description else record.model}'
                title = f'{title} S/N {record.serial_number} из очета за {record.report.get_report_month()}'
                mail_message_for_center(
                    record.report.service_center,
                    subject,
                    title,
                    request.POST.get('message'),
                )
                return redirect('record-for-staff', report_pk)
    return redirect('staff_home')


# удаление детали из ремонта менеджером
@user_passes_test(staff_validation)
def RecordPartStaffDelete(request):
    if request.method == 'POST':
        if 'delete' in request.POST:
            part_pk = request.POST.get('delete')
            if part_pk:
                part = get_object_or_404(ReportsParts, pk=int(part_pk))
                record = part.record
                part.delete()
                # подготовка сообщения менеджеру
                subject = 'Удалена деталь из одного из ваших ремонтов.'
                title = f'Удалена деталь "{part.title}" из ремонта изделия'
                title = f'{title} {record.model_description if record.model_description else record.model}'
                title = f'{title} S/N {record.serial_number} (очет за {record.report.get_report_month()})'
                mail_message_for_center(
                    record.report.service_center,
                    subject,
                    title,
                    request.POST.get('message'),
                )
                return redirect('record-for-staff', record.pk)
    return redirect('staff_home')


# --------------------------- AJAX -------------------------------------------

# обработка AJAX скрипта динамической формы
def load_codes_data(request):
    from django.db.models import Q

    groups = None
    codes = None
    code_id = None
    if 'product' in request.GET and request.GET.get('product'):
        product_id = request.GET.get('product')
        codes = Codes.objects.filter(
            Q(product_id=product_id) | Q(product_id=None),
            is_folder=False,
            is_active=True,
        ).order_by('code')
        groups = Codes.objects.filter(
            Q(product_id=product_id) | Q(product_id=None),
            is_folder=True,
            is_active=True,
        ).order_by('code')
        code_id = 0
        if 'code' in request.GET and request.GET.get('code'):
            code_id = int(request.GET.get('code'))
    return render(
        request,
        'reports/codes_list_get.html',
        {'groups': groups, 'codes': codes, 'select_id': code_id},
    )


# обработка AJAX скрипта динамической формы
def load_models_data(request):
    models_list = None
    if 'product' in request.GET and request.GET.get('product'):
        product_id = request.GET.get('product')
        models_list = Models.objects.filter(product_id=product_id).order_by(
            'title'
        )
    return render(
        request, 'reports/models_list_get.html', {'groups': models_list}
    )


# обработка AJAX скрипта динамической формы
def load_work_price_data(request):
    price = 0
    if (
        'code' in request.GET
        and 'report' in request.GET
        and request.GET.get('code')
        and request.GET.get('report')
    ):
        code_id = request.GET.get('code')
        report_id = request.GET.get('report')
        code = get_object_or_404(Codes, pk=code_id)
        report = get_object_or_404(Reports, pk=report_id)
        price_dict = GetPrices(code, report.service_center)
        if 'price' in price_dict:
            price = price_dict['price']
    return render(request, 'reports/price_get.html', {'price': price})


# удаление отета
def ReportDelete(request, report_pk):
    report = get_object_or_404(Reports, pk=report_pk)
    if request.user.is_superuser or request.user == report.user:
        report.delete()
        messages.success(request, 'Отчет успешно удален !')
        return redirect('user_home')
    else:
        return HttpResponseForbidden()


# удаление отета
def RecordDelete(request, report_pk):
    record = get_object_or_404(ReportsRecords, pk=report_pk)
    report = record.report
    if request.user.is_superuser or request.user == report.user:
        record.delete()
        messages.success(request, 'Запись успешно удалена !')
        report.save()
        return redirect(report.get_absolute_url())
    else:
        return HttpResponseForbidden()


# --------------------------- ЗАКАЗ ДЕТАЛЕЙ -------------------------------------------


class OrderedParts(LoginRequiredMixin, TemplateView):
    """список деталей, заказаннх пользователем"""

    template_name = 'reports/ordered_parts.html'

    def get_context_data(self):
        context = super().get_context_data()
        parts = (
            ReportsParts.objects.filter(
                order_date__isnull=False,
                record__report__service_center__user=self.request.user,
            )
            .values('record', 'send_number', 'send_date', 'title', 'count')
            .exclude(
                Q(record__report__status=STATUS_ACCEPTED)
                | Q(record__report__status=STATUS_PAYMENT)
            )
        )
        if 'filter' in self.request.GET:
            parts = parts.filter(title__iregex=self.request.GET['filter'])
        context['parts'] = parts
        records = ReportsRecords.objects.filter(
            pk__in=parts.values('record').distinct()
        ).values(
            'pk',
            'report',
            'product__title',
            'model_description',
            'serial_number',
        )
        context['records'] = records
        reports = Reports.objects.filter(
            pk__in=records.values('report').distinct()
        )
        context['reports'] = reports
        context['obj_count'] = parts.count()
        context['center'] = self.request.user.service_center
        context['form'] = UserPartForm(self.request.GET)
        return context


@user_passes_test(staff_validation)
def getRecordData(request):
    """передача в шаблон страницы 'Заказанные таблицы' сведений о ремонте"""

    if 'recordId' in request.GET and request.GET.get('recordId'):
        record = get_object_or_404(
            ReportsRecords, pk=int(request.GET.get('recordId'))
        )
        return render(
            request, 'reports/get_record_data.html', {'record': record}
        )
    return HttpResponse(
        '<h5 class="my-3 text-center">Ошибка получения данных ...</h5>'
    )


class StaffOrderedParts(LoginRequiredMixin, StaffUserMixin, TemplateView):
    """список всех заказанных деталей"""

    template_name = 'reports/ordered_parts_staff.html'

    def get_context_data(self):
        """формирование контекста страницы"""

        from django.core.paginator import Paginator

        context = super().get_context_data()
        context['title'] = 'Все заказанные детали'

        # поготовливаем qset деталей с учетом фильтра
        parts = ReportsParts.objects.filter(order_date__isnull=False).order_by(
            'record__pk', 'order_date'
            ).values(
            'pk',
            'title',
            'record__pk',
            'send_number',
            'count',
            'send_date',
            'order_date',
            'record__model_description',
            'record__report__service_center__pk',
        )
        # если пользователь - менеджер региона
        user_regions = ServiceRegions.objects.filter(
            staff_user=self.request.user
        ).values('title')
        if user_regions:
            regions = ', '.join([region['title'] for region in user_regions])
            context['title'] = f'Детали, заказанные для регионов "{regions}"'
            parts = parts.filter(
                Q(order_date__isnull=False)
                & (
                    Q(
                        record__report__service_center__region__staff_user=self.request.user
                    )
                )
            )
        # если пользователь менеджер по проверке отчетов
        if not user_regions and ServiceCenters.objects.filter(
            staff_user=self.request.user
        ).values('pk'):
            context['title'] = f'Детали, заказанные вашими СЦ '
            parts = parts.filter(
                Q(order_date__isnull=False)
                & (
                    Q(
                        record__report__service_center__staff_user=self.request.user
                    )
                )
            )
        if parts.exists():
            if 'show_send' in self.request.GET and self.request.GET['show_send']:
                parts = parts.order_by('send_date')
                if 'send_start' in self.request.GET and self.request.GET['send_start']:
                    parts = parts.filter(send_date__gte=self.request.GET['send_start'])
                if 'send_end' in self.request.GET and self.request.GET['send_end']:
                    parts = parts.filter(send_date__lte=self.request.GET['send_end'])    
            else:
                parts = parts.filter(send_number__isnull=True)
            if 'filter' in self.request.GET and self.request.GET['filter']:
                parts = parts.filter(title__iregex=self.request.GET['filter'])
            if 'center' in self.request.GET and self.request.GET['center']:
                parts = parts.filter(
                    record__report__service_center__pk=int(
                        self.request.GET['center']
                    )
                )
            if 'period' in self.request.GET and self.request.GET['period']:
                period_str = self.request.GET['period']
                if period_str.isdigit():
                    last_date = datetime.datetime.now() - datetime.timedelta(
                        days=int(self.request.GET['period'])
                    )
                    parts = parts.filter(order_date__lt=last_date)

        # подговка данных о сервисных центрах, отчетах и ремонтах
        cnt = parts.values('record__report__service_center__pk').distinct()
        centers = ServiceCenters.objects.filter(id__in=cnt).values(
            'pk',
            'title',
            'region__title',
            'region__staff_user',
            'post_addr',
        )

        # настройка пагинации
        paginator = Paginator(centers, 999)
        if (
            ('show_send' in self.request.GET and self.request.GET['show_send'])
            and not (
                'send_start' in self.request.GET
                and self.request.GET['send_start']
                )
            and not (
                'send_end' in self.request.GET
                and self.request.GET['send_end']
                )
        ):
            paginator = Paginator(centers, 5)
        num = 0
        for part in parts:
            part['show_record'] = (
                True if (
                    (num == 0)
                    or (
                        parts[num-1]['record__pk']
                        != part['record__pk']
                        )
                    )
                else False
            )
            num += 1

        page_number = self.request.GET.get('page')
        context['page_obj'] = paginator.get_page(page_number)
        context['centers'] = centers
        context['parts'] = parts
        context['obj_count'] = parts.count()
        context['form'] = UserPartForm(self.request.GET)
        return context


@user_passes_test(staff_validation)
def SendParts(request):
    """ Обработка формы на странице списка заказов деталей """

    def get_order_data(parts_pk):
        """ Формирование стуктуры заказа. """

        parts_data = ReportsParts.objects.filter(pk__in=parts_pk).values_list(
                'record__report__service_center__pk', 'pk'
            )
        order_data = []
        for part in parts_data:
            need_add = True
            for item in order_data:
                if item['center'] == part[0]:
                    item['parts'].append(part[1])
                    need_add = False
                    break
            if need_add:
                order_data.append({'center': part[0],'parts': [part[1]]})   
        return order_data

    def GetPartOrderPdf(order_data):
        """ Подготовка Pdf файла этикетки """
       
        buffer = order_part_blank(order_data)
        response = HttpResponse(content_type='application/pdf')
        response[
            'Content-Disposition'
        ] = 'attachment; filename=renova_part_orders.pdf'
        response.write(buffer.getvalue())
        buffer.close()
        return response

    def get_order_data_xls(order_data, mode):
        response = HttpResponse(content_type='application/ms-excel')
        response[
            'Content-Disposition'
        ] = 'attachment; filename=orders.xls'
        if mode == 'export_data':
            workBook = part_order_xls(order_data)
        elif mode == 'export_data_list':
            workBook = part_order_list_xls(order_data)
        workBook.save(response)
        return response

    def SaveSendPartsData(parts, send_date, number):
        """ Запись данных от отправке деталей """

        for part in parts:
            part.send_date = send_date
            part.send_number = number
            part.save()
        mail_send_parts(parts)

    if request.method == 'POST':
        # создаем список кллючей таблицы Parts из параметров запроса
        parts_pk = list(map(int, request.POST.getlist('parts')))
        if not parts_pk:
            messages.error(request, 'Ни одна деталь не выбрана !')
            return redirect('staff-ordered-parts')
        # если список не пуст определеям режим работы
        if request.POST['submit_mode'] == 'print_label':
            # Режим - печать ярлыка
            return GetPartOrderPdf(get_order_data(parts_pk))      
        elif request.POST['submit_mode'] == 'save_data':
            # Режим - запись данных об отрправке
            # Проверяем заполнение формы
            parts = ReportsParts.objects.filter(
                pk__in=parts_pk,
                record__report__service_center__pk=request.POST['center']
                )
            if not parts:
                messages.error(request, 'Для этого сервисного центра детали не выбраны !')
                return redirect('staff-ordered-parts')  
            if not request.POST['number']:
                messages.error(request, 'Не указан номер отправления !')
                return redirect('staff-ordered-parts')
            if not request.POST['send_date']:
                messages.error(request, 'Не указана дата отправки !')
                return redirect('staff-ordered-parts')
            # Записываем данные об отправке
            SaveSendPartsData(
                parts,
                request.POST['send_date'],
                request.POST['number']
            )
            messages.success(request, 'Данные об отправке записаны !')
        else:
            # режим экспорта таблицы
            return get_order_data_xls(
                get_order_data(parts_pk),
                request.POST['submit_mode'] 
                )

    return redirect('staff-ordered-parts')

# -------------------------- СПЕЦИАЛЬНЫЕ ФУНКЦИИ ---------------------------------------


@user_passes_test(superuser_validation)
def accept_all(request):
    records = ReportsRecords.objects.filter(
        verified=False, report__status=STATUS_RECEIVED
    )
    for record in records:
        record.verified = True
        record.save()
    reports = Reports.objects.filter(status=STATUS_VERIFIED)
    for report in reports:
        report.status = STATUS_ACCEPTED
        report.save()
        email = report.service_center.user.email
        mail_note = """
        Для оплаты ваших услуг нам необхоидм Акт выполненных работ и Счет на ВСЮ сумуу по отчету
        (за работы + за детали + за выезд). Если вы еще не отправляли нам эти документы почтой или по ЭДО,
        пожалуйста отправьте сканы по электронной почте на адерс sergey.shaginyan@re-nova.com.
        В теме писмьао пожалуйста укажите название своего сервисного центра и отчетный месяц.
        """
        if email:
            SendReportSatus('shagi80@mail.ru', report, mail_note)
    return redirect('reports_list')
