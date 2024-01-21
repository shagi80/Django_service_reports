from django.contrib import admin

from . import models


@admin.register(models.ActStatusHistory)
class ActHistoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'act', 'status', 'created_at', 'user')
    list_display_links = ('id', 'act')
    search_fields = ['act__center__title']


@admin.register(models.ActMember)
class ActMemberAdmin(admin.ModelAdmin):
    list_display = ('id', 'act', 'created_at', 'user')
    list_display_links = ('id', 'act')
    search_fields = ['act__center__title']


@admin.register(models.NonRepairabilityAct)
class ActAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'doc_date',
        'center',
        'product',
        'model_description',
        'serial_number',
    )
    list_display_links = ('doc_date', 'center')
    search_fields = ['center__title', 'serial_number']


@admin.register(models.ActDocumnent)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'act')
    list_display_links = ('title',)
    search_fields = ['act__center__title']
