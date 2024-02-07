from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.contrib.auth.decorators import user_passes_test
from django.http import Http404, HttpResponseForbidden, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DetailView, View, DeleteView
from django.contrib import messages
from main.my_validators import SuperUserMixin, StaffUserMixin, GeneralStaffUserMixin
from main.views import MyFormMessagesView
from .forms import *
from .models import ServiceContacts
from main.my_validators import staff_validation


class ServiceCentersRegionList(LoginRequiredMixin, StaffUserMixin, ListView):
    model = ServiceRegions
    template_name = 'servicecentres/centres_regions_list.html'
    context_object_name = 'regions'
    extra_context = {'title': 'Регионы доставки запчастей'}
    paginate_by = 10
    allow_empty = True


class ServiceCentersList(LoginRequiredMixin, StaffUserMixin, ListView):
    model = ServiceCenters
    template_name = 'servicecentres/centres_list.html'
    context_object_name = 'centres'
    extra_context = {'title': 'Сервисные центры'}
    paginate_by = 20

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        form = CenterFilterForm(self.request.GET)
        context['form'] = form
        context['obj_count'] = self.object_list.count()
        return (context)

    def get_queryset(self):
        centres = ServiceCenters.objects.all()
        if self.request.GET.get("staff_user", '') != '':
            centres = centres.filter(staff_user=self.request.GET.get("staff_user"))
        if self.request.GET.get("active_only", '') != '':
            centres = centres.filter(is_active=True)
        if self.request.GET.get("filter", '') != '':
            centres = centres.filter(Q(title__iregex=self.request.GET.get("filter")) | Q(city__iregex=self.request.GET.get("filter")))
        if self.request.GET.get("region", '') != '':
            centres = centres.filter(region__pk=self.request.GET.get("region"))
        return centres


class ServiceCentersAdd(LoginRequiredMixin, GeneralStaffUserMixin, MyFormMessagesView, CreateView):
    form_class = CenterCreateForm
    template_name = 'servicecentres/centres_add.html'
    extra_context = {'title': 'Добавление сервисного центра'}
    success_message = 'Сервисный центр успешно добавлен'

    def get_success_url(self):
        if 'close' in self.request.POST:
            return reverse_lazy('centres_list_page')
        else:
            return reverse_lazy('centres_update_page', args=(self.object.id,))

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['def_user'] = self.request.user
        return kwargs


class ServiceCenterUpdate(LoginRequiredMixin, StaffUserMixin, MyFormMessagesView, UpdateView):
    model = ServiceCenters
    form_class = CenterCreateForm
    template_name = 'servicecentres/centres_add.html'
    success_message = 'Обьект успешно изменен'

    def test_func(self):
        return (
            self.request.user == self.get_object().staff_user
            or self.request.user.is_superuser
            or self.request.user.groups.filter(name='GeneralStaff').exists()
            )

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['def_user'] = self.request.user
        return kwargs

    def get_success_url(self):
        if 'close' in self.request.POST:
            if 'next' in self.request.GET:
                return self.request.GET['next']+'#Item-'+str(self.object.pk)
            else:
                return reverse_lazy('centres_list_page')
        else:
            return self.request.path_info

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['title'] = obj.title
        context['object'] = obj
        return (context)


class ServiceCentersContactsList(LoginRequiredMixin, StaffUserMixin, ListView):
    model = ServiceContacts
    template_name = 'servicecentres/centres_contacts_list.html'
    context_object_name = 'contacts'
    extra_context = {'title': 'Контакты сервисных центров'}
    paginate_by = 21

    def get_queryset(self):
        centres = ServiceContacts.objects.all()
        if self.request.GET.get("filter", '') != '':
            centres = centres.filter(Q(service_center__title__iregex=self.request.GET.get("filter")) | Q(name__iregex=self.request.GET.get("filter")))
        return centres


class ServiceCentersContactsByCenter(LoginRequiredMixin, StaffUserMixin, ListView):
    model = ServiceContacts
    template_name = 'servicecentres/centres_contacts_list.html'
    context_object_name = 'contacts'
    extra_context = {'title': 'Контакты ораганизации '}
    allow_empty = True

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        context['center'] = ServiceCenters.objects.get(pk=self.kwargs['center_pk'])
        return (context)

    def get_queryset(self):
        return ServiceContacts.objects.filter(service_center_id=self.kwargs['center_pk']).select_related('service_center')


class ServiceContactAdd(LoginRequiredMixin, StaffUserMixin, MyFormMessagesView, CreateView):
    form_class = ContactCreateForm
    template_name = 'servicecentres/centres_contact_add.html'
    extra_context = {'title': 'Добавление контакта'}
    success_message = 'Контакт успешно добавлен'

    def form_valid(self, form):
        if (
            self.request.user.is_superuser
            or self.request.user.groups.filter(name='GeneralStaff').exists()
            or form.cleaned_data['service_center'].staff_user == self.request.user
        ):
            return super().form_valid(form)
        return self.form_invalid(form)

    def get_success_url(self):
        if 'close' in self.request.POST:
            return reverse_lazy('centres_contact_page', args=(self.object.service_center_id,))
        else:
            return reverse_lazy('contact_add_page')

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['staff_user'] = self.request.user
        return kwargs


class ServiceContactUpdate(LoginRequiredMixin, StaffUserMixin, MyFormMessagesView, UpdateView):
    model = ServiceContacts
    form_class = ContactCreateForm
    template_name = 'servicecentres/centres_contact_add.html'
    extra_context = {'title': 'Изменение контакта'}
    success_message = 'Контакт успешно изменен'

    def test_func(self):
        return (
            self.request.user == self.get_object().service_center.staff_user
            or self.request.user.is_superuser
            or self.request.user.groups.filter(name='GeneralStaff').exists()
            )

    def get_context_data(self, *, object_list=None, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context['center_id'] = obj.service_center_id
        return (context)

    def get_success_url(self):
        return reverse_lazy('centres_contact_page', args=(self.object.service_center_id,))

    def get_form_kwargs(self, *args, **kwargs):
        kwargs = super().get_form_kwargs(*args, **kwargs)
        kwargs['staff_user'] = self.request.user
        return kwargs


def ContactDelete(request, contact_pk):
    obj = get_object_or_404(ServiceContacts, pk=contact_pk)
    if (
        request.user.is_superuser
        or request.user == obj.service_center.staff_user
        or request.user.groups.filter(name='GeneralStaff').exists()
    ):
        reverse_id = obj.service_center_id
        obj.delete()
        messages.success(request, 'Контакт успешно удален')
        return redirect('centres_contact_page', reverse_id)
    else:
        return HttpResponseForbidden()


@user_passes_test(staff_validation)
def CentersListExport(request):
    """ выгрузка данных о сервисных центрах в соответствии с фильтром """
    
    import xlwt

    centres = ServiceCenters.objects.all()
    if request.GET.get("staff_user", '') != '':
        centres = centres.filter(staff_user=request.GET.get("staff_user"))
    if request.GET.get("active_only", '') != '':
        centres = centres.filter(is_active=True)
    if request.GET.get("filter", '') != '':
        centres = centres.filter(Q(title__iregex=request.GET.get("filter")) | Q(city__iregex=request.GET.get("filter")))
    if request.GET.get("region", '') != '':
        centres = centres.filter(region__pk=request.GET.get("region"))

    response = HttpResponse(content_type='application/ms-excel')
    disp = f'attachment; filename="SenterListData.xls"'
    response['Content-Disposition'] = disp
    workBook = xlwt.Workbook(encoding='utf-8')
    workSheet = workBook.add_sheet("Sheet_1")

    # Sheet header, first row
    boldStyle = xlwt.XFStyle()
    boldStyle.font.bold = True
    row_num = 0
    workSheet.write(row_num, 0, f'Данные о сервисных центрах', boldStyle)

    # Table header, third row
    row_num = 2
    workSheet.row(row_num).height = 600
    headerStyle = xlwt.easyxf('font: bold off, color black; borders: left thin, right thin, top thin, bottom thin;\
     pattern: pattern solid, fore_color white, fore_colour gray25; align: horiz center, vert top;')
    headerStyle.alignment.wrap = 1
    columns = ['№', 'Актив',  'Код', 'Регион', 'Наименование', 'Город', 'Адрес', 'Почтовый адрес', 'Особые условия',\
                'Примечание', 'Пользователь', 'E-mail пользователя', 'Контакты', 'Менеджер', 'Рэйтинг']
    for col_num in range(len(columns)):
        workSheet.write(row_num, col_num, columns[col_num], headerStyle)
        workSheet.col(col_num).width = 5000

    # Sheet body, remaining rows
    style = xlwt.easyxf('align: vert top;')
    row_num_str = 0
    for center in centres:
        row_num += 1
        row_num_str += 1
        workSheet.col(0).width = 1000
        workSheet.write(row_num, 0, str(row_num_str), style)
        workSheet.col(1).width = 2000
        workSheet.write(row_num, 1, 'активен' if center.is_active else 'не активен', style)
        workSheet.col(2).width = 3000
        workSheet.write(row_num, 2, center.code, style)
        workSheet.col(3).width = 3000
        workSheet.write(row_num, 3, center.region.title, style)
        workSheet.write(row_num, 4, center.title, style)
        workSheet.write(row_num, 5, center.city, style)
        workSheet.write(row_num, 6, center.addr, style)
        workSheet.write(row_num, 7, center.post_addr, style)
        workSheet.write(row_num, 8, center.conditions, style)
        workSheet.write(row_num, 9, center.note, style)
        workSheet.write(row_num, 10, center.user.username, style)
        workSheet.write(row_num, 11, center.user.email, style)
        string = ""
        for contact in center.servicecontacts_set.all():
            if contact.name:
                string = string + contact.name + ', '
            if contact.funct:
                string = string + contact.funct + ', '
            if contact.tel_num:
                string = string + contact.tel_num + ', '
            if contact.email:
                string = string + contact.email + ', '
            if contact.note:
                string = string + contact.note + ', '
            string = string + '\n'
        workSheet.write(row_num, 12, string, style)
        workSheet.write(row_num, 13, center.staff_user.username, style)
        workSheet.col(14).width = 3000
        workSheet.write(row_num, 14, center.grade, style)

    workBook.save(response)
    return response

