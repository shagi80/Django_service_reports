from django.contrib import admin
from .models import ServiceRegions, ServiceCenters, ServiceContacts


class ServiceRegionsAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'staff_user')
    list_display_links = ('id', 'title')
    search_fields = ('title',)


class ServiceCentersAdmin(admin.ModelAdmin):
    # настройка списка новостей
    list_display = ('id', 'is_active', 'code',  'title', 'region', 'city', 'user', 'staff_user')
    list_display_links = ('id', 'title')
    search_fields = ('title', 'city')
    list_filter = ('is_active', 'region', 'user', 'staff_user', 'city')


class ServiceContactsAdmin(admin.ModelAdmin):
    list_display = ('id', 'service_center', 'name', 'funct')
    list_display_links = ('id', 'name')
    search_fields = ('name', 'service_center__title')
    list_filter = ('service_center',)


admin.site.register(ServiceContacts, ServiceContactsAdmin)

admin.site.register(ServiceRegions, ServiceRegionsAdmin)

admin.site.register(ServiceCenters, ServiceCentersAdmin)


