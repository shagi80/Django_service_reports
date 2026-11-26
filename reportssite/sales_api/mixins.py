from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError


class UpdatedAfterFilterMixin:
    """Единый стандарт фильтрации по интервалу ?updated_after= и ?updated_to= для ListAPIView"""
    updated_field = 'updated_at'

    def _parse_iso_datetime(self, param_name):
        raw_value = self.request.query_params.get(param_name)
        if not raw_value:
            return None

        normalized_date = raw_value.replace(' ', '+')
        parsed_date = parse_datetime(normalized_date)
        if parsed_date is None:
            raise ValidationError({
                param_name: 'Неверный формат даты. Используйте ISO 8601 (например, 2026-11-18T12:00:00Z).'
            })
        return parsed_date

    def get_updated_range(self):
        """Возвращает кортеж (updated_after, updated_to) и валидирует их соотношение."""
        updated_after = self._parse_iso_datetime('updated_after')
        updated_to = self._parse_iso_datetime('updated_to')

        if updated_after and updated_to and updated_after >= updated_to:
            raise ValidationError({
                'updated_to': 'Параметр updated_to должен быть строго больше updated_after.'
            })

        return updated_after, updated_to

    def filter_by_updated_after(self, queryset):
        updated_after, updated_to = self.get_updated_range()

        if updated_after is not None:
            queryset = queryset.filter(**{f'{self.updated_field}__gt': updated_after})

        if updated_to is not None:
            queryset = queryset.filter(**{f'{self.updated_field}__lte': updated_to})

        return queryset
