from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError


class UpdatedAfterFilterMixin:
    """Единый стандарт фильтрации по параметру ?updated_after= для всех ListAPIView"""
    updated_field = 'updated_at'

    def filter_by_updated_after(self, queryset):
        updated_after = self.request.query_params.get('updated_after')
        if updated_after:
            normalized_date = updated_after.replace(' ', '+')
            parsed_date = parse_datetime(normalized_date)
            if parsed_date is None:
                raise ValidationError({
                    'updated_after': 'Неверный формат даты. Используйте ISO 8601 (например, 2026-11-18T12:00:00Z).'
                })
            queryset = queryset.filter(**{f'{self.updated_field}__gt': parsed_date})
        return queryset

