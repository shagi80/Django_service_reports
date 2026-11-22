from django.contrib import admin
from .models import (
    Counterparty,
    EmployeeProfile,
    Storage,
    Group,
    GoodsItem,
    Remnant,
    Price,
)


class EmployeeProfileInline(admin.TabularInline):
    """Отображение привязанных пользователей прямо внутри карточки контрагента"""
    model = EmployeeProfile
    extra = 1
    autocomplete_fields = ['user']


@admin.register(Counterparty)
class CounterpartyAdmin(admin.ModelAdmin):
    list_display = ('code', 'company_name', 'inn')
    search_fields = ('code', 'company_name', 'inn')
    ordering = ('company_name',)
    inlines = [EmployeeProfileInline]


@admin.register(Storage)
class StorageAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'city', 'addr', 'contact', 'work_time')
    list_filter = ('city',)
    search_fields = ('code', 'name', 'city', 'addr')
    ordering = ('name',)


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'owner_code', 'updated_at')
    search_fields = ('code', 'name', 'owner_code')
    readonly_fields = ('updated_at',)
    ordering = ('owner_code', 'name')


@admin.register(GoodsItem)
class GoodsItemAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'owner_code', 'unit_name', 'unit_code', 'updated_at')
    list_filter = ('unit_name',)
    search_fields = ('code', 'name', 'owner_code')
    readonly_fields = ('updated_at',)
    list_per_page = 50
    ordering = ('name',)


@admin.register(Remnant)
class RemnantAdmin(admin.ModelAdmin):
    list_display = ('storage_code', 'item_code', 'count', 'updated_at')
    list_filter = ('storage_code',)
    search_fields = ('storage_code', 'item_code')
    readonly_fields = ('updated_at',)
    list_per_page = 50
    ordering = ('storage_code', 'item_code')


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ('counterparty_code', 'item_code', 'price', 'updated_at')
    list_filter = ('counterparty_code',)
    search_fields = ('counterparty_code', 'item_code')
    readonly_fields = ('updated_at',)
    list_per_page = 50
    ordering = ('counterparty_code', 'item_code')
