""" модели для админки """
from django.contrib import admin
from .models import ReportDocumnent, RecordDocumnent


class ReportDocumnentAdmin(admin.ModelAdmin):
    """ модель документов отчета для админки """
    list_display = ('id', 'report', 'title', 'number', 'date')
    list_display_links = ('id',)
    list_filter = ('report',)


class RecordDocumnentAdmin(admin.ModelAdmin):
    """ модель документов ремонтв для админки """
    list_display = ('id', 'record', 'title', 'number', 'date')
    list_display_links = ('id',)
    list_filter = ('record',)


admin.site.register(ReportDocumnent, ReportDocumnentAdmin)  

admin.site.register(RecordDocumnent, RecordDocumnentAdmin)