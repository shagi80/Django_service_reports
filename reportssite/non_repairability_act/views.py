import datetime, calendar
from threading import Thread
from django.db import models
from django.db.models import Q
from django.http import HttpResponse, HttpResponseNotFound, Http404
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import ListView
from django.views.generic.edit import (
    CreateView,
    DeleteView,
    ProcessFormView,
    FormView,
    UpdateView,
)
from django.views.generic.detail import DetailView

from main.my_validators import StaffUserMixin, UserMixin
from mail.views import mail_message_for_center, mail_message_for_staff
from reports.models import Models
from products.models import Codes
from . import models, forms, pdf_generator

# ------------------------------------- ПРЕДСТАВЛЕНИЯ ИНТЕРФЕЙСА СЕРВИСА ------------------------------------


class OwnerUserMixin(UserPassesTestMixin):
    def test_func(self):
        return (
            self.request.user.is_active
            and self.request.user.service_center() == self.get_object().center
        )


class ActFormMixin(FormView):
    model = models.NonRepairabilityAct
    template_name = 'non_repairability_act/create_update.html'
    form_class = forms.ActEditForm

    def form_valid(self, form):
        # получаем и проверяем формсет добавления документов
        formset = forms.ActFileFormset(
            self.request.POST, self.request.FILES, instance=form.instance
        )
        if not formset.is_valid():
            form.add_error(
                '',
                f'Не удалось добавить один или несколько файлов. '
                f'При добавлении документа необходимо указать тип документа, '
                f'номер и дату документа, выбрать файл одного из следующих форматов '
                f'"pdf", "doc", "docx", "jpg", "png", "xlsx", "xls", "jpeg"',
            )
            return self.form_invalid(form)
        # запоминаем "режим" - create или update
        is_create = not form.instance.pk
        # записываем объект и формсет
        result = super().form_valid(form)
        formset.save()
        # если это создание объекта - присваиваем статус "черновик"
        if is_create:
            form.instance.add_status(models.ActStatus.DRAFT, self.request.user)
        # если нажата кнопка "Сохранить"
        if 'submit-save' in self.request.POST:
            messages.success(self.request, 'Акт успешно сохранен !')
        # если нажата кнопка "Отправить"
        if 'submit-send' in self.request.POST:
            # проверяем Акт перед отправкой
            send_errors = form.instance.send_errors
            if send_errors:
                for error in send_errors:
                    form.add_error(error, send_errors[error])
                return self.form_invalid(form)
            # изменения статуса
            if form.instance.status.status in [
                models.ActStatus.DRAFT,
                models.ActStatus.REFINEMENT,
            ]:
                if form.instance.status.status == models.ActStatus.DRAFT:
                    form.instance.add_status(
                        models.ActStatus.SEND, self.request.user
                    )
                else:
                    form.instance.add_status(
                        models.ActStatus.SEND_AGAIN, self.request.user
                    )
                messages.success(self.request, 'Акт успешно отправлен !')
                # отправка уведомления по e-mail
                subject = (
                    f'Получен Акт НРП от {form.instance.center.title}'
                    f'({form.instance.center.city}).'
                )
                message = None
                Thread(
                    target=mail_message_for_staff,
                    args=(form.instance.center, subject, subject, message),
                ).start()
            else:
                form.add_error(
                    '',
                    [
                        'Сбой в поределении статуста, сообщите администрации сайта !',
                    ],
                )
                return self.form_invalid(form)
        return result

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = (
            f'Акт неремонтопригодности №{self.object.pk}'
            if self.object
            else 'Новый акт неремонтопригодности'
        )
        context['exist_files'] = (
            self.object.documents.all() if self.object else None
        )
        context['file_formset'] = forms.ActFileFormset()
        return context


class ActCreateView(UserMixin, ActFormMixin, CreateView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs


class ActUpdateView(OwnerUserMixin, ActFormMixin, UpdateView):
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        if not self.object.status.status in [
            models.ActStatus.DRAFT,
            models.ActStatus.REFINEMENT,
        ]:
            kwargs['disabled'] = True
        return kwargs


class GetModelView(LoginRequiredMixin, ProcessFormView):
    def get(self, request):
        if 'product' in request.GET and request.GET['product']:
            models_set = Models.objects.filter(
                product_id=request.GET['product']
            ).order_by('title')
            return render(
                request,
                'non_repairability_act/get_models.html',
                {'values': models_set},
            )
        return HttpResponseNotFound()


class GetCodeView(LoginRequiredMixin, ProcessFormView):
    def get(self, request):
        if 'product' in request.GET and request.GET['product']:
            product_id = request.GET.get('product')
            select = (
                int(request.GET.get('select'))
                if request.GET.get('select')
                else None
            )
            codes = Codes.objects.filter(
                product_id=product_id,
                is_folder=False,
                is_active=True,
            ).order_by('code')
            groups = Codes.objects.filter(
                product_id=product_id,
                is_folder=True,
                is_active=True,
            ).order_by('code')
            return render(
                request,
                'non_repairability_act/get_codes.html',
                {'groups': groups, 'codes': codes, 'select': select},
            )
        return HttpResponseNotFound()


class DelFileView(OwnerUserMixin, ProcessFormView):
    def post(self, request):
        if 'pk' in request.POST and request.POST['pk']:
            obj = get_object_or_404(models.ActDocumnent, pk=request.POST['pk'])
            obj.delete()
            return HttpResponse(200)
        return HttpResponseNotFound()


# ------------------------------------- ПРЕДСТАВЛЕНИЯ ИНТЕРФЕЙСА МЕНЕДЖЕРА ------------------------------------


class ActDetailView(DetailView):
    model = models.NonRepairabilityAct
    context_object_name = 'act'

    def get_object(self):
        try:
            obj = models.NonRepairabilityAct.objects.select_related(
                'center', 'product', 'model'
            ).get(pk=self.kwargs['pk'])
        except:
            raise Http404
        return obj

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context[
            'title'
        ] = f'Акт №{self.object.pk} от {self.object.doc_date.strftime("%d.%m.%Y")}.'
        return context


class ActDeatailForStaffView(StaffUserMixin, ActDetailView):
    template_name = 'non_repairability_act/staff_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['dev_location'] = models.DeviceLocation
        return context


class ActDetailCheckView(ActDetailView):
    template_name = 'non_repairability_act/check.html'

    def get_object(self):
        obj = super().get_object()
        if obj.status.status != models.ActStatus.DRAFT:
            return obj
        raise Http404()


class ActStaffChangeStatusView(StaffUserMixin, ProcessFormView):
    def post(self, request):
        if 'act_pk' in request.POST and request.POST['act_pk']:
            obj = get_object_or_404(
                models.NonRepairabilityAct, pk=request.POST['act_pk']
            )
            obj.add_status(request.POST['new_status'], request.user)
            subject = (
                f'Акт НРП №{obj.pk} от {obj.doc_date.strftime("%Y-%m-%d")}'
                f' {obj.status.get_status_display()}.'
            )
            message = (
                request.POST['message'] if 'message' in request.POST else None
            )
            # действие при отправке на доработку
            # if (request.POST['new_status'] == models.ActStatus.REFINEMENT and message):
            #  obj.add_member(message, True, request.user)
            # действия при подтверждении Акта
            if request.POST['new_status'] == models.ActStatus.CONFIRMED:
                # сбрасываем замечания
                obj.member_for_user = None
                obj.save(update_fields=['member_for_user'])
                # определяем дальнейшую судьбу изделия
                if 'dev-location' in request.POST:
                    obj.device_location = request.POST['dev-location']
                    obj.save(update_fields=['device_location'])
                    message = f'Дальнешая судьба изделия: {obj.get_device_location_display()}.'
            Thread(
                target=mail_message_for_center,
                args=(obj.center, subject, subject, message),
            ).start()
            return redirect('act-staff-detail', pk=request.POST['act_pk'])
        return HttpResponseNotFound()


class ActAddMemberView(StaffUserMixin, ProcessFormView):
    def post(self, request):
        if 'act_pk' in request.POST and request.POST['act_pk']:
            obj = get_object_or_404(
                models.NonRepairabilityAct, pk=request.POST['act_pk']
            )
            obj.add_member(
                request.POST['text'],
                True if request.POST['mode'] == 'for_center' else False,
                request.user,
            )
            return redirect('act-staff-detail', pk=request.POST['act_pk'])
        return HttpResponseNotFound()


class ActDeleteMemberView(StaffUserMixin, ProcessFormView):
    def post(self, request):
        if 'act_pk' in request.POST and request.POST['act_pk']:
            obj = get_object_or_404(
                models.NonRepairabilityAct, pk=request.POST['act_pk']
            )
            obj.delete_member(request.POST['member_pk'])
            return redirect('act-staff-detail', pk=request.POST['act_pk'])
        return HttpResponseNotFound()


class ActDeleteUserMemberView(StaffUserMixin, ProcessFormView):
    def post(self, request):
        if 'act_pk' in request.POST and request.POST['act_pk']:
            obj = get_object_or_404(
                models.NonRepairabilityAct, pk=request.POST['act_pk']
            )
            obj.member_for_user = None
            obj.save(update_fields=['member_for_user'])
            return redirect('act-staff-detail', pk=request.POST['act_pk'])
        return HttpResponseNotFound()


# ------------------------------------- ОБЩИЕ ПРЕДСТАВЛЕНИЯ  ------------------------------------


class ActDeleteView(LoginRequiredMixin, DeleteView):
    model = models.NonRepairabilityAct
    context_object_name = 'act'
    success_url = reverse_lazy('act-list')

    def form_valid(self, form):
        if self.request.user.is_staff:
            obj = self.get_object()
            subject = f'Акт НРП №{obj.pk} от {obj.doc_date.strftime("%Y-%m-%d")} удален.'
            message = (
                self.request.POST['message']
                if 'message' in self.request.POST
                else None
            )
            Thread(
                target=mail_message_for_center,
                args=(obj.center, subject, subject, message),
            ).start()
        messages.success(self.request, 'Акт успешно удален !')
        return super().form_valid(form)


class ActListView(LoginRequiredMixin, ListView):
    model = models.NonRepairabilityAct
    template_name = 'non_repairability_act/list.html'
    context_object_name = 'acts'
    paginate_by = 10

    def get_queryset(self):
        qset = models.NonRepairabilityAct.objects.select_related(
            'product', 'center'
        ).all()
        if not self.request.user.is_staff:
            qset = qset.filter(center=self.request.user.service_center())
        elif not self.request.user.is_superuser:
            id = [
                act.id
                for act in qset
                if act.status.status != models.ActStatus.DRAFT
            ]
            qset = qset.filter(id__in=id)
        if self.request.GET.get('filter', '') != '':
            qset = qset.filter(
                Q(shop__iregex=self.request.GET.get('filter'))
                | Q(client__iregex=self.request.GET.get('filter'))
                | Q(serial_number__iregex=self.request.GET.get('filter'))
            )
        if self.request.GET.get('service_center', '') != '':
            qset = qset.filter(center=self.request.GET.get('service_center'))
        if self.request.GET.get('staff_user', '') != '':
            qset = qset.filter(
                service_center__staff_user=self.request.GET.get('staff_user')
            )
        if (
            'status' in self.request.GET
            and self.request.GET.get('status', '') != ''
        ):
            id = [
                act.id
                for act in qset
                if act.status.status == self.request.GET.get('status')
            ]
            qset = qset.filter(id__in=id)
        if (
            'year' in self.request.GET
            and 'month' in self.request.GET
            and self.request.GET.get('year', '') != ''
            and self.request.GET.get('month', '') != ''
        ):
            year = int(self.request.GET.get('year', ''))
            month = int(self.request.GET.get('month', ''))
            month_start = datetime.date(year, month, 1)
            month_end = datetime.date(
                year, month, calendar.monthrange(year, month)[1]
            )
            qset = qset.filter(
                doc_date__gte=month_start, doc_date__lte=month_end
            )
        return qset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = forms.ActsFilterForm(self.request.GET)
        context['obj_count'] = self.object_list.count()
        return context


def download_pdf(request, pk):
    """prepare and response pdf-document"""
    act = get_object_or_404(models.NonRepairabilityAct, pk=pk)
    if request.user.is_staff or request.user == act.center.user:
        buffer = pdf_generator.prepare_pdf(act)
        response = HttpResponse(content_type='application/pdf')
        response[
            'Content-Disposition'
        ] = f'attachment; filename=renova_nrp_{pk}.pdf'
        response.write(buffer.getvalue())
        buffer.close()
        return response
    return Http404()
