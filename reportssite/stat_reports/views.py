""" представления модуля статистики """
import csv


from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.views.generic import ListView
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.db.models import Sum
import xlwt
from main.my_validators import StaffUserMixin, staff_validation
from main.business_logic import STATUS_ACCEPTED
from reports.models import Reports, ReportsRecords
from .forms import MangerWorkFilterForm


class ManagerWork(LoginRequiredMixin, StaffUserMixin, ListView):
    """ представление Работа Менеджера """
    model = Reports
    template_name = 'stat_reports/manager_work.html'
    context_object_name = 'records'
    extra_context = {'title': 'Принято всеми менеджерами:'}
    paginate_by = 30

    def get_queryset(self):
        records = ReportsRecords.objects.filter(verified=True)
        manager_id = self.request.GET.get("manager", '')
        start_date = self.request.GET.get("start_date", '')
        end_date = self.request.GET.get("end_date", '')
        if manager_id:
            records = records.filter(report__service_center__staff_user__pk=manager_id)
        if start_date:
            records = records.filter(verified_date__gte=start_date)
        if end_date:
            records = records.filter(verified_date__lte=end_date)
        if self.request.GET.get("errors_only", ''):
            records = records.exclude(errors=None)
        records = records.order_by("-verified_date", "report")
        return records
     
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        manager_id = self.request.GET.get("manager", '') 
        if manager_id:
            user = get_object_or_404(User, pk=manager_id)
            context['title'] = f'Принято менеджером {user}:'
        context['obj_count'] = self.object_list.count()
        context['form'] = MangerWorkFilterForm(self.request.GET)
        return context
    

class SumForPayment(LoginRequiredMixin, StaffUserMixin, ListView):
    """ представление Суммы для оплаты """
    model = Reports
    template_name = 'stat_reports/sum_for_payment.html'
    context_object_name = 'reports'
    extra_context = {'title': 'Суммы для оплаты:'}
    paginate_by = 50

    def get_queryset(self):
        reports = Reports.objects.filter(status=STATUS_ACCEPTED).order_by('service_center')
        if not(self.request.user.is_superuser or self.request.user.groups.filter(name='GeneralStaff')):
            reports = reports.filter(service_center__staff_user=self.request.user)
        return reports
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not(self.request.user.is_superuser or self.request.user.groups.filter(name='GeneralStaff')):
            context['title'] = f'Суммы для оплаты по СЦ менедежера {self.request.user}:'
        total_sum = self.object_list.aggregate(total_sum=Sum('total_cost'))
        context['total'] = f"{self.object_list.count()} отчетов на сумму {total_sum['total_sum']} руб"
        return context


@user_passes_test(staff_validation)
def export_sum_for_payment(request):
    """ выгрузка отчета по суммам для оплаты в эксель """

    # Создание книги, наименование файла, создание листа, наименование листа
    reports = Reports.objects.filter(status=STATUS_ACCEPTED).order_by('service_center')
    caption = f'Суммы для оплаты'
    if not(request.user.is_superuser or request.user.groups.filter(name='GeneralStaff')):
        reports = reports.filter(service_center__staff_user=request.user)
        caption = f'Суммы для оплаты ({request.user})'
    disp = f'attachment; filename="Sum for payment.xls"'
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = str(disp)
    workBook = xlwt.Workbook(encoding='utf-8')
    workSheet = workBook.add_sheet('main')

    # Заголовок старницы
    boldStyle = xlwt.XFStyle()
    boldStyle.font.bold = True
    row_num = 0
    workSheet.write(row_num, 0, caption, boldStyle)
    row_num = 1
    total_sum =reports.aggregate(total_sum=Sum('total_cost'))
    workSheet.write(row_num, 0, f"{reports.count()} отчетов на сумму {total_sum['total_sum']} руб", boldStyle)

    # Заголовок таблицы
    row_num = 3
    workSheet.row(row_num).height = 400
    headerStyle = xlwt.easyxf('font: bold off, color black; borders: left thin, right thin, top thin, bottom thin;\
     pattern: pattern solid, fore_color white, fore_colour gray25; align: horiz center, vert top;')
    headerStyle.alignment.wrap = 1
    columns = ['№',  'Отчет', 'За детали', 'За выезд', 'За работы', 'Итого', 'Акт и счет']
    for col_num in range(len(columns)):
        workSheet.write(row_num, col_num, columns[col_num], headerStyle)

    # Тело таблицы - построчный вывод данных
    style = xlwt.XFStyle()
    row_num_str = 0
    for report in reports:
        row_num += 1
        row_num_str += 1
        workSheet.col(0).width = 1000
        workSheet.write(row_num, 0, str(row_num_str), style)
        workSheet.col(1).width = 15000
        workSheet.write(row_num, 1, report.__str__(), style)
        workSheet.col(2).width = 3000
        workSheet.write(row_num, 2, report.total_part, style)
        workSheet.col(3).width = 3000
        workSheet.write(row_num, 3, report.total_move, style)
        workSheet.col(4).width = 3000
        workSheet.write(row_num, 4, report.total_work, style)
        workSheet.col(5).width = 3000
        workSheet.write(row_num, 5, report.total_cost, style)
        workSheet.col(6).width = 20000
        workSheet.write(row_num, 6, report.get_report_documents(), style)

    workBook.save(response)
    return response


@user_passes_test(staff_validation)
def export_sum_for_payment_to_csv(request):
    """ выгрузка даннх о суммах в оплату для экспорта в 1С """

    response = HttpResponse(
        content_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="sum_for_pay.txt"'},
    )
    #response.write('asdf'.encode('ansi'))

    Dialect = csv.excel
    Dialect.quoting = csv.QUOTE_ALL
    writer = csv.writer(response, dialect = Dialect)
    reports = Reports.objects.filter(status=STATUS_ACCEPTED).order_by('service_center')
    for report in reports:
        act = report.reportdocumnent_set.filter(title='act').first()
        row = [report.service_center.code, report.service_center.title,
               report.total_part, report.total_move, report.total_work
               ]
        if act:
            row.extend([act.number, act.date.strftime("%d.%m.%Y"),])
        else:
            row.extend(['', ''])
        row.append(f'за {report.get_report_month()}')
        writer.writerow(row)

    return response