from rest_framework import serializers

from .models import Storage, Group, GoodsItem, Remnant, Price


class StorageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Storage
        fields = [
            'code',
            'name',
            'city',
            'addr',
            'contact',
            'work_time',
            'note',
        ]
        extra_kwargs = {
            'code': {'validators': []}
        }


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = [
            'code',
            'owner_code',
            'name',
        ]
        extra_kwargs = {
            'code': {'validators': []}
        }


class GoodsItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = GoodsItem
        fields = [
            'code',
            'owner_code',
            'name',
            'unit_code',
            'unit_name',
            'updated_at',
        ]
        extra_kwargs = {
            'code': {'validators': []}
        }


class ItemRemnantSerializer(serializers.ModelSerializer):
    """Остаток товара на конкретном складе"""
    class Meta:
        model = Remnant
        fields = [
            'storage_code',
            'item_code',
            'count',
            'updated_at',
        ]
        validators = []


class CatalogItemSerializer(serializers.ModelSerializer):
    """Единый сериализатор позиции каталога с ценой и остатками"""
    unit = serializers.CharField(source='unit_name')
    price = serializers.SerializerMethodField()
    remnants = serializers.SerializerMethodField()

    class Meta:
        model = GoodsItem
        fields = [
            'code',
            'owner_code',
            'name',
            'unit',
            'unit_code',
            'price',
            'remnants',
            'updated_at',
        ]

    def get_price(self, obj):
        # Берем цену из предварительно загруженного словаря в context (без лишних запросов к БД)
        return self.context.get('prices_map', {}).get(obj.code)

    def get_remnants(self, obj):
        # Берем остатки из предварительно загруженного словаря в context
        return self.context.get('remnants_map', {}).get(obj.code, [])


class PriceSerializer(serializers.ModelSerializer):
    """Цена товара для контрагента"""
    class Meta:
        model = Price
        fields = [
            'counterparty_code',
            'item_code',
            'price',
            'updated_at',
        ]
        validators = []