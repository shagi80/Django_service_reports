""" представления загрузки документов """
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.core.mail import send_mail
from reports.models import Reports
from .models import ReportDocumnent, RecordDocumnent
from .forms import ReportDocumentForm, RecordDocumentForm


# загрузка документа отчета
@login_required
def AddReportDocumet(request, report_pk):
    """ загрузка документа к отчету """
    if request.method == 'POST':
        form = ReportDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Файл успешно загружен на сервер !')
            report = Reports.objects.get(pk=report_pk)
            if report and request.user != report.service_center.staff_user:
                SendMailToStaff(report)
        else:
            for key in form.errors.keys():
                messages.error(request, form.errors[key])          
    return redirect('report_page', report_pk)


# удаление документа отчета
@login_required
def DeleteReportDocumet(request, report_pk):
    """ загрузка документа к отчету """
    if request.method == 'POST':
        doc = get_object_or_404(ReportDocumnent, pk=request.POST['document'])
        doc.delete()
        messages.success(request, 'Документ успешно удален !')        
    return redirect('report_page', report_pk)


# отправка письма менеджеру о поступлении документа
def SendMailToStaff(report):
    """ отправка электронного письма менеджеру """
    email = report.service_center.staff_user.email
    if email:
        msg = f'К отчету {report.service_center} за {report.get_report_month()} добавлен новый документ.\n\n'
        msg = msg + 'Это письмо сформированно автоматическа, отвечать на него не нужно.'
        send_mail(
            'RENOVA. Получен новый документ.',
            msg,
            'report_service@re-nova.com',
            #['shagi80@mail.ru'],
            [email],
            fail_silently=False,
        )


# загрузка документа ремонта
@login_required
def AddRecordDocumet(request, record_pk):
    """ загрузка документа к отчету """
    if request.method == 'POST':
        form = RecordDocumentForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Файл успешно загружен на сервер !')
            #record = ReportsRecords.objects.get(pk=record_pk)
            #if record and request.user != record.report.service_center.staff_user:
             #   SendMailToStaff(record)
        else:
            for key in form.errors.keys():
                messages.error(request, form.errors[key])          
    return redirect('record_update_page', record_pk)


# удаление документа ремонта
@login_required
def DeleteRecordDocumet(request, record_pk):
    """ удаление документа ремонта """
    if request.method == 'POST':
        doc = get_object_or_404(RecordDocumnent, pk=request.POST['document'])
        doc.delete()
        messages.success(request, 'Документ успешно удален !')        
    return redirect('record_update_page', record_pk)

