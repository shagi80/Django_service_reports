from django.contrib import admin
from .models import Reports, ReportsRecords, ReportsParts


class ReportsAdmin(admin.ModelAdmin):
  list_display = ('id', 'service_center', 'report_date', 'status')
  list_display_links = ('id', 'service_center', 'report_date')
  list_filter = ('service_center',)


class ReportRecordsAdmin(admin.ModelAdmin):
  list_display = ('id', 'report', 'product', 'model', 'serial_number')
  list_display_links = ('id',)
  list_filter = ('report__service_center',)
  search_fields = ('serial_number',)


class ReportsPartsAdmin(admin.ModelAdmin):
  list_display = ('id',  'record', 'title', 'order_date', 'count')
  list_display_links = ('id',)
  list_filter = ('record__report__service_center',)
  search_fields = ('record__serial_number',)


admin.site.register(Reports, ReportsAdmin)
admin.site.register(ReportsRecords, ReportRecordsAdmin)
admin.site.register(ReportsParts, ReportsPartsAdmin)