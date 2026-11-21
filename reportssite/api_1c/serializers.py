from rest_framework import serializers
from main.models import ChangeLogs
from servicecentres.models import ServiceContacts, ServiceRegions, ServiceCenters
from products.models import MainProducts, Models, Codes
from reports.models import ReportsRecords, Reports
from non_repairability_act.models import NonRepairabilityAct


# ========================================== #
# 1. СЕРИАЛИЗАЦИЯ ДАННЫХ МОДЕЛИ CHANGELOG
# ========================================== #

class ChangeLogSerializer(serializers.ModelSerializer):
    """Сериализатор для логов изменений"""
   
    class Meta:
        model = ChangeLogs
        fields = ['id', 'model', 'record_id', 'action_on_model']


# ========================================== #
# 2. СЕРИАЛИЗАЦИЯ МОДЕЛЕЙ СПРАВОЧНИКОВ
# ========================================== #

class ServiceRegionsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ServiceRegions """
    
    class Meta:
        model = ServiceRegions
        fields = ['id', 'title', 'staff_user']


class ServiceCentersSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ServiceCenters """
    
    class Meta:
        model = ServiceCenters
        fields = ['id', 'code', 'title', 'city', 'region', 'addr', 'post_addr', 'conditions', 'free_parts', 
                  'grade', 'note', 'is_active', 'user', 'staff_user', 'price_type']


class ServiceContactsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели ServiceContacts"""
    
    class Meta:
        model = ServiceContacts
        fields = ['id', 'name', 'service_center', 'funct', 'tel_num', 'email', 'note']


class MainProductsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели MainProducts"""

    class Meta:
        model = MainProducts
        fields = ['id', 'title', 'short_title', 'valid_date', 'guarantee_period', 'check_serial']


class ModelsSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Models"""

    class Meta:
        model = Models
        fields = ['id', 'title', 'code_chars',  'west_id',  'east_id', 'product']


class CodesSerializer(serializers.ModelSerializer):
    """Сериализатор для модели Codes"""

    class Meta:
        model = Codes
        fields = ['id', 'product', 'parent', 'is_folder', 'code', 'title', 'repair_type', 'is_active']

 
# ========================================== #
# 3. СЕРИАЛИЗАЦИЯ МОДЕЛЕЙ ОТЧЕТОВ И РЕМОНТОВ
# ========================================== #

class ReportsRecordSerializer(serializers.ModelSerializer):
    """Сериализатор для записей отчетов (Ремонтов)"""
    
    product_id = serializers.ReadOnlyField()
    model_id = serializers.ReadOnlyField()
    code_id = serializers.ReadOnlyField()
    report_id = serializers.ReadOnlyField()
    parent_act_id = serializers.ReadOnlyField()
    
    status = serializers.ReadOnlyField()

    class Meta:
        model = ReportsRecords
        fields = [
            'id', 'product_id', 'model_id', 'work_type', 'client_type',
            'client', 'client_phone', 'client_addr', 'client_email',
            'model_description', 'serial_number', 'buy_date', 'start_date',
            'end_date', 'work_cost', 'move_cost', 'problem_description',
            'work_description', 'code_id', 'note', 'report_id', 'parts_cost',
            'total_cost', 'verified', 'factory', 'main_date', 'shift',
            'errors', 'remarks', 'have_general_errors', 'verified_date',
            'order_parts', 'parent_act_id', 'status'
        ]

class ReportFullSerializer(serializers.ModelSerializer):
    """Полный сериализатор отчета со всеми вложенными ремонтами для 1С"""
    
    service_center_id = serializers.ReadOnlyField()
    user_id = serializers.ReadOnlyField()
    
    records = ReportsRecordSerializer(
        many=True, 
        read_only=True, 
        source='reportsrecords_set'
    )
    
    class Meta:
        model = Reports
        fields = [
            'id', 'service_center_id', 'user_id', 'report_date', 'status',
            'total_cost', 'total_work', 'total_part', 'total_move',
            'records_count', 'verified_count', 'have_fault', 'pay_date', 
            'send_date', 'note', 'records'
        ]


# ========================================== #
# 4. СЕРИАЛИЗАЦИЯ АКТОВ НРП
# ========================================== #

class NonRepairabilityActFullSerializer(serializers.ModelSerializer):
    """Сериализатор акта неремонтопригодности"""
    
    # ReadOnly поля для связанных ForeignKeys
    center_id = serializers.ReadOnlyField(source='center.id')
    product_id = serializers.ReadOnlyField(source='product.id')
    model_id = serializers.ReadOnlyField(source='model.id')
    code_id = serializers.ReadOnlyField(source='code.id')
    
    # Динамическое поле status, использующее property модели.
    status = serializers.SerializerMethodField()

    class Meta:
        model = NonRepairabilityAct
        fields = [
            'id', 'center_id', 'product_id', 'model_id', 'code_id',
            'model_description', 'serial_number', 'work_type', 'completeness',
            'problem_description', 'client_type', 'client', 'client_phone',
            'client_addr', 'client_email', 'shop', 'shop_phone', 'shop_addr',
            'work_description', 'decree', 'device_location', 'note',
            'member_for_user', 'doc_date', 'buy_date', 'receipt_date',
            'status'
        ]

    def get_status(self, obj):
        # Проверяем, что property 'status' вернуло объект истории
        status_obj = obj.status
        if status_obj:
            return status_obj.status  
        return None
