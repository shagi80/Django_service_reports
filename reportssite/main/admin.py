from django.contrib import admin
from .models import ChangeLogs


class ChangeLogsAdmin(admin.ModelAdmin):
  list_display = ('changed', 'model', 'user', 'record_id', 'data', 'ipaddress', 'action_on_model',)
  readonly_fields = ('user', )
  list_filter = ('model', 'action_on_model',)


admin.site.register(ChangeLogs, ChangeLogsAdmin)


admin.site.site_title = 'Отчеты сервисных центров'

admin.site.site_header = 'Отчеты сервисных центров'