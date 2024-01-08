from django.contrib import admin
from .models import *


class MainProductsAdmin(admin.ModelAdmin):
    # настройка списка новостей
    list_display = ('id', 'title')
    list_display_links = ('id', 'title')
    search_fields = ('title',)


class ModelsAdmin(admin.ModelAdmin):
    # настройка списка новостей
    list_display = ('id', 'product', 'title', 'code_chars', 'west_id', 'east_id')
    list_display_links = ('id', 'title')
    search_fields = ('title',)


class CodesAdmin(admin.ModelAdmin):
    # настройка списка новостей
    list_display = ('id', 'product', 'code', 'title', 'repair_type')
    list_display_links = ('id', 'title', 'code')
    search_fields = ('title', 'code')
    list_filter = ('product',)


class BasePriceAdmin(admin.ModelAdmin):
    # настройка списка новостей
    list_display = ('id', 'product', 'repair_type', 'price')
    list_display_links = ('id', 'product', 'repair_type', 'price')
    search_fields = ('product',)
    list_filter = ('product',)
    ordering = ('product', 'repair_type')


class CentersPricesAdmin(admin.ModelAdmin):
    # настройка списка новостей
    list_display = ('id', 'service_center', 'product', 'code', 'price')
    list_display_links = ('id', 'code')
    search_fields = ('service_center', 'product', 'code',)
    list_filter = ('service_center',)
    ordering = ('service_center', 'product', 'group', 'code')


admin.site.register(CentersPrices, CentersPricesAdmin)


admin.site.register(MainProducts, MainProductsAdmin)

admin.site.register(Models, ModelsAdmin)

admin.site.register(Codes, CodesAdmin)

admin.site.register(BasePrice, BasePriceAdmin)
