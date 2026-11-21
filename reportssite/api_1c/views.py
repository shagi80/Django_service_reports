import json
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.pagination import PageNumberPagination
from django.utils import timezone
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes
from django.core.paginator import Paginator

from main.models import ChangeLogs
from servicecentres.models import ServiceContacts, ServiceRegions, ServiceCenters
from products.models import MainProducts, Models, Codes
from reports.models import Reports
from non_repairability_act.models import NonRepairabilityAct
from .serializers import (
    ChangeLogSerializer,
    ServiceRegionsSerializer,
    ServiceCentersSerializer,
    ServiceContactsSerializer,
    ReportFullSerializer,
    MainProductsSerializer,
    ModelsSerializer,
    CodesSerializer,
    NonRepairabilityActFullSerializer
    )
from .mixins import BasicAuthMixin, JsonIdValidationMixin, SingleIdValidationMixin, DateRangeValidationMixin


# Настройка пагинации
class CustomPagination(PageNumberPagination):
    """Кастомная пагинация с ограничением размера страницы"""
    page_size = 100
    max_page_size = 1000
    page_size_query_param = 'page_size'


# ========================================== #
# 1. ПРОВЕРКА СВЯЗИ И АВТОРИЗАЦИИ
# ========================================== #

@extend_schema(
    tags=['Server'],
    summary="Проверка доступности API",
    description="Эндпоинт для проверки работоспособности API. Не требует авторизации.",
    responses={
        200: OpenApiResponse(
            description="API работает",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={'status': 'ok', 'message': 'API is working'},
                )
            ]
        )
    }
)
class HealthCheckView(APIView):
    """Проверка доступности API"""
    
    def get(self, request):
        return Response({
            'status': 'ok',
            'message': 'API is working'
        })


@extend_schema(
    tags=['Server'],
    summary="Проверка авторизации",
    description="Проверяет, что Basic Auth работает корректно. Требует авторизации.",
    responses={
        200: OpenApiResponse(
            description="Авторизация успешна",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={'status': 'success', 'message': 'Authentication successful', 'user': 'username'},
                )
            ]
        ),
        401: OpenApiResponse(
            description="Ошибка авторизации",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'unauthorized',
                    value={'detail': 'Invalid username/password'},
                )
            ]
        )
    }
)
class AuthTestView(BasicAuthMixin, APIView):
    """Проверка авторизации"""
    
    def get(self, request):
        return Response({
            'status': 'success',
            'message': 'Authentication successful',
            'user': request.user.username
        })


@extend_schema(
    tags=['Server'],
    summary="Текущее время сервера",
    description="Возвращает текущее время сервера с учетом часового пояса. Не требует авторизации.",
    responses={
        200: OpenApiResponse(
            description="Время успешно получено",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={
                        'success': True,
                        'server_time': '2026-05-20T17:30:00.123456+03:00',
                        'timestamp': 1716215400,
                        'timezone': 'Europe/Moscow'
                    },
                )
            ]
        )
    }
)
class ServerTimeView(APIView):
    """Возвращает текущее время сервера"""
    
    def get(self, request):
        now = timezone.now()
        return Response({
            'success': True,
            'server_time': now.isoformat(),
            'timestamp': int(now.timestamp()),
            'timezone': timezone.get_current_timezone_name()
        })


# ========================================== #
# 2. ЛОГИ ИЗМЕНЕНИЙ СПРАВОЧНИКОВ
# ========================================== #

@extend_schema(
    tags=['Change Logs'],
    summary="Количество записей в диапазоне дат",
    description="Возвращает количество записей в ChangeLogs, которые были изменены в указанном диапазоне дат.",
    parameters=[
        OpenApiParameter(
            name='start_date',
            description='Дата в ISO формате (YYYY-MM-DDTHH:MM:SS). Например: 2026-01-01T00:00:00',
            required=True,
            type=str,
            location=OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            name='end_date',
            description='Дата в ISO формате (YYYY-MM-DDTHH:MM:SS). Например: 2026-01-01T00:00:00',
            required=True,
            type=str,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Успешный ответ",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={'success': True, 'after_date': '2026-01-01T00:00:00', 'count': 42},
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации даты",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'invalid_date',
                    value={'error': 'Invalid date format', 'message': 'after_date must be in ISO format'},
                )
            ]
        ),
        401: OpenApiResponse(description="Требуется авторизация")
    }
)
class ChangeLogsCountView(BasicAuthMixin, APIView):
    """Количество записей после даты"""
    
    def get(self, request):
        validator = DateRangeValidationMixin()
        
        start_date, end_date, error_response = validator.get_and_validate_date(self.request)
        if error_response:
            return ChangeLogs.objects.none()
        
        count = ChangeLogs.objects.filter(changed__gte=start_date, changed__lt=end_date).count()
        
        return Response({
            'success': True,
            'after_date': request.GET.get('after_date'),
            'count': count
        })

@extend_schema(
    tags=['Change Logs'],
    summary="Получить полные данные логов с пагинацией в диапазоне дат",
    description="Возвращает все поля записей ChangeLogs, измененных в диапазоне указанных дат. Поддерживает пагинацию.",
    parameters=[
        OpenApiParameter(
            name='start_date',
            description='Дата в ISO формате (YYYY-MM-DDTHH:MM:SS)',
            required=True,
            type=str,
            location=OpenApiParameter.QUERY
        ),
                OpenApiParameter(
            name='end_date',
            description='Дата в ISO формате (YYYY-MM-DDTHH:MM:SS)',
            required=True,
            type=str,
            location=OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            name='page',
            description='Номер страницы',
            required=False,
            type=int,
            location=OpenApiParameter.QUERY
        ),
        OpenApiParameter(
            name='page_size',
            description='Размер страницы (максимум 200, по умолчанию 100)',
            required=False,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Страница не найдена")
    }
)
class ChangeLogsDateRangeView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные логов с поддержкой пагинации"""

    serializer_class = ChangeLogSerializer
    pagination_class = CustomPagination
    
    def get_queryset(self):
        validator = DateRangeValidationMixin()
        
        start_date, end_date, error_response = validator.get_and_validate_date(self.request)
        if error_response:
            return ChangeLogs.objects.none()
        
        return (ChangeLogs.objects
                .filter(changed__gte=start_date, changed__lt=end_date)
                .select_related('user')
                .order_by('changed'))
    
    def list(self, request, *args, **kwargs):
        validator = DateRangeValidationMixin()
        
        start_date, end_date, error_response = validator.get_and_validate_date(request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
        
        return super().list(request, *args, **kwargs)
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({
            'after_date': self.request.GET.get('after_date')
        })
        return context


# ========================================== #
# 3. ПОЛУЧЕНИЕ ЭЛЕМЕНТОВ СПРАВОЧНИКОВ ПО id
# ========================================== #

@extend_schema(
    tags=['Entities'],
    summary="Получить регион сервиса по ID",
    description="Возвращает данные региона сервисного центра",
    parameters=[
        OpenApiParameter(
            name='id',
            description='Уникальный ID региона в базе данных',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Контакт не найден")
    }
)
class ServiceRegionsDetailView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные региона сервисного центра по ID"""

    serializer_class = ServiceRegionsSerializer
    pagination_class = None  
    
    def get_queryset(self):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return ServiceRegions.objects.none()
        
        # Возвращаем queryset с одной записью
        return (ServiceRegions.objects
                .filter(id=target_id)
                .order_by('id'))
    
    def list(self, request, *args, **kwargs):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
            
        # 3. Проверка существования записи в базе данных
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'error': 'Not Found',
                'message': f'Service region with id={target_id} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. Извлекаем ОДИН конкретный объект из queryset
        instance = queryset.first()
        
        # 5. Сериализуем как одиночный объект (БЕЗ many=True)
        serializer = self.get_serializer(instance)
        
        # 6. Возвращаем чистый JSON-объект
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Entities'],
    summary="Получить сервисный центр по ID",
    description="Возвращает данные конкретного сервисного центра.",
    parameters=[
        OpenApiParameter(
            name='id',
            description='Уникальный ID сервисного центра в базе данных',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Контакт не найден")
    }
)
class ServiceCentersDetailView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные сервисного центра по ID"""

    serializer_class = ServiceCentersSerializer
    pagination_class = None  # Отключаем пагинацию, так как ищем одну запись
    
    def get_queryset(self):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return ServiceCenters.objects.none()
        
        # Возвращаем queryset с одной записью
        return (ServiceCenters.objects
                .filter(id=target_id)
                .select_related('region')
                .order_by('id'))
    
    def list(self, request, *args, **kwargs):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
            
        # 3. Проверка существования записи в базе данных
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'error': 'Not Found',
                'message': f'Service center with id={target_id} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. Извлекаем ОДИН конкретный объект из queryset
        instance = queryset.first()
        
        # 5. Сериализуем как одиночный объект (БЕЗ many=True)
        serializer = self.get_serializer(instance)
        
        # 6. Возвращаем чистый JSON-объект
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Entities'],
    summary="Получить контакт по ID",
    description="Возвращает данные конкретного контакта.",
    parameters=[
        OpenApiParameter(
            name='id',
            description='Уникальный ID контакта в базе данных',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Контакт не найден")
    }
)
class ServiceContactDetailView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные контакта по ID"""
    serializer_class = ServiceContactsSerializer
    pagination_class = None  # Отключаем пагинацию, так как ищем одну запись
    
    def get_queryset(self):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return ServiceContacts.objects.none()
        
        # Возвращаем queryset с одной записью
        return (ServiceContacts.objects
                .filter(id=target_id)
                .select_related('service_center')
                .order_by('id'))
    
    def list(self, request, *args, **kwargs):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
            
        # 3. Проверка существования записи в базе данных
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'error': 'Not Found',
                'message': f'Contact with id={target_id} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # 4. Извлекаем ОДИН конкретный объект из queryset
        instance = queryset.first()
        
        # 5. Сериализуем как одиночный объект (БЕЗ many=True)
        serializer = self.get_serializer(instance)
        
        # 6. Возвращаем чистый JSON-объект
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Entities'],
    summary="Получить вид продукции по ID",
    description="Возвращает данные конкретного вида продукции. Структура класса полностью идентична ChangeLogsAllDataView.",
    parameters=[
        OpenApiParameter(
            name='id',
            description='Уникальный ID вида продукции в базе данных',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Вид продукции не найден")
    }
)
class MainProductDetailView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные вида продукции по ID"""

    serializer_class = MainProductsSerializer
    pagination_class = None 
    
    def get_queryset(self):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return MainProducts.objects.none()
        
        return (MainProducts.objects
                .filter(id=target_id)
                .order_by('id'))
    
    def list(self, request, *args, **kwargs):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
            
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'error': 'Not Found',
                'message': f'MainProduct with id={target_id} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        instance = queryset.first()
        serializer = self.get_serializer(instance)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Entities'],
    summary="Получить модель продукции по ID",
    description="Возвращает данные конкретной модели продукции.",
    parameters=[
        OpenApiParameter(
            name='id',
            description='Уникальный ID модели продукции в базе данных',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Модель продукции не найден")
    }
)
class ModelDetailView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные модели продукции по ID"""

    serializer_class = ModelsSerializer
    pagination_class = None  
    
    def get_queryset(self):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Models.objects.none()
        
        return (Models.objects
                .filter(id=target_id)
                .select_related('product')
                .order_by('id'))
    
    def list(self, request, *args, **kwargs):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
            
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'error': 'Not Found',
                'message': f'Model with id={target_id} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        instance = queryset.first()
        serializer = self.get_serializer(instance)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema(
    tags=['Entities'],
    summary="Получить код неисправности по ID",
    description="Возвращает данные конкретного кода неисправности.",
    parameters=[
        OpenApiParameter(
            name='id',
            description='Уникальный ID кода неисправности в базе данных',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY
        )
    ],
    responses={
        200: OpenApiResponse(description="Успешный ответ"),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация"),
        404: OpenApiResponse(description="Код неисправности не найден")
    }
)
class CodeDetailView(BasicAuthMixin, generics.ListAPIView):
    """Получить данные кода неисправности по ID"""

    serializer_class = CodesSerializer
    pagination_class = None
    
    def get_queryset(self):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Codes.objects.none()
        
        return (Codes.objects
                .filter(id=target_id)
                .select_related('product', 'parent')
                .order_by('id'))
    
    def list(self, request, *args, **kwargs):
        validator = SingleIdValidationMixin()
        
        target_id, error_response = validator.get_and_validate_id(self.request)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
            
        queryset = self.get_queryset()
        if not queryset.exists():
            return Response({
                'error': 'Not Found',
                'message': f'Code with id={target_id} does not exist'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        instance = queryset.first()
        serializer = self.get_serializer(instance)
        
        return Response(serializer.data, status=status.HTTP_200_OK)


# ========================================== #
# 4. РАБОТА С ОТЧЕТАМИ О РЕМОНТАХ
# ========================================== #

@extend_schema(
    tags=['Reports'],
    summary="Количество новых отчетов после указанного id",
    description="Возвращает количество новых отчетов, имюещих ID более указанного.",
    parameters=[
        OpenApiParameter(
            name='after_id',
            description='Id c которого начиется поиск (число)',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY)
    ],
    responses={
        200: OpenApiResponse(
            description="Успешный ответ",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={'success': True, 'after_date': '2026-01-01T00:00:00', 'count': 42},
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации даты",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'invalid_date',
                    value={'error': 'Invalid date format', 'message': 'after_date must be in ISO format'},
                )
            ]
        ),
        401: OpenApiResponse(description="Требуется авторизация")
    }
)
class ReportsNewCountView(BasicAuthMixin, APIView):
    """Количество новых отчетов после указанного id"""
    
    def get(self, request):
        validator = SingleIdValidationMixin()
        
        after_id, error_response = validator.get_and_validate_id(
            request, 
            param_name='after_id'
        )
        if error_response:
            return error_response
        
        count = Reports.objects.filter(id__gt=after_id).count()
        
        return Response({
            'success': True,
            'after_id': request.GET.get('after_id'),
            'count': count
        })

@extend_schema(
    tags=['Reports'],
    summary="Получить данные новых отчетов с пагинацией",
    description="Возвращает полные данные новых отчетов, которые были созданы после указанного ID. "
                "Поддерживает пагинацию для постраничного получения данных.",
    parameters=[
        OpenApiParameter(
            name='after_id',
            description='ID отчета, после которого нужно получить данные',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='page',
            description='Номер страницы',
            required=False,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='page_size',
            description='Размер страницы (максимум 100, по умолчанию 50)',
            required=False,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class ReportsNewView(BasicAuthMixin, APIView):
    """Получить данные новых отчетов после указанного ID с пагинацией"""
    
    serializer_class = ReportFullSerializer

    def get(self, request):
        # 1. Валидация after_id        
        validator = SingleIdValidationMixin()
        
        after_id, error_response = validator.get_and_validate_id(
            request, 
            param_name='after_id'
        )
        if error_response:
            return error_response

        # 2. Проверка существования отчета
        if not Reports.objects.filter(id=after_id).exists():
            return Response({
                'error': 'Not Found',
                'message': f'Report with id={after_id} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 3. Параметры пагинации
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 50)
        
        try:
            page = int(page)
            page_size = int(page_size)
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 50
            if page < 1:
                page = 1
        except ValueError:
            page = 1
            page_size = 50
        
        # 4. Получаем queryset
        queryset = (Reports.objects
            .filter(id__gt=after_id)
            .select_related('service_center')
            .order_by('id'))
        
        # 5. Пагинация
        paginator = Paginator(queryset, page_size)
        
        if page > paginator.num_pages and paginator.num_pages > 0:
            return Response({
                'error': 'Not Found',
                'message': f'Page {page} does not exist. Total pages: {paginator.num_pages}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        current_page = paginator.get_page(page)
        
        # 6. Сериализация
        serializer = ReportFullSerializer(current_page, many=True)
        
        # 7. Ответ
        return Response({
            'success': True,
            'after_id': after_id,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count
            },
            'results': serializer.data
        })
      
@extend_schema(
    tags=['Reports'],
    summary="Получить данные отчетов по списку ID",
    description="Возвращает полные данные отчетов по переданному списку ID. "
                "Включает все поля отчета и связанные с ним записи ReportsRecords. "
                "Максимум 100 ID за запрос.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'ids': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'example': [2141, 2142, 2143, 2144, 2145],
                    'description': 'Список ID отчетов (максимум 100)'
                }
            },
            'required': ['ids']
        }
    },
    responses={
        200: OpenApiResponse(
            description="Успешный ответ",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={
                        'success': True,
                        'requested_count': 2,
                        'returned_count': 2,
                        'results': [
                            {
                                'id': 2141,
                                'service_center_id': 3,
                                'report_date': '2026-01-15',
                                'note': None,
                                'user_id': 5,
                                'status': 'draft',
                                'total_cost': 15000,
                                'total_work': 10000,
                                'total_part': 5000,
                                'total_move': 0,
                                'records_count': 3,
                                'verified_count': 0,
                                'have_fault': False,
                                'pay_date': None,
                                'send_date': None,
                                'records': [
                                    {
                                        'id': 101,
                                        'serial_number': 'SN12345',
                                        'work_cost': 5000,
                                        'parts_cost': 2000,
                                        'total_cost': 7000,
                                        'status': 'work_end'
                                    }
                                ]
                            }
                        ]
                    },
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'invalid_json',
                    value={'error': 'Bad Request', 'message': 'Invalid JSON format.'},
                ),
                OpenApiExample(
                    'missing_ids',
                    value={'error': 'Bad Request', 'message': 'Field "ids" is required and must be a list of integers.'},
                ),
                OpenApiExample(
                    'too_many_ids',
                    value={'error': 'Bad Request', 'message': 'Too many IDs. Maximum 100 allowed per request.'},
                )
            ]
        ),
        401: OpenApiResponse(
            description="Требуется авторизация",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'unauthorized',
                    value={'detail': 'Invalid username/password'},
                )
            ]
        )
    }
)
class ReportsByIdsView(BasicAuthMixin, APIView):
    """Получить данные отчетов по списку ID"""
    
    serializer_class = ReportFullSerializer
    
    def post(self, request): 
        
        # 1. Валидация списка ID
        validator = JsonIdValidationMixin()
        data_ids, error_response = validator.get_and_validate_ids(request, max_limit=100)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
        
        # 2. Получаем queryset
        queryset = (Reports.objects
                    .filter(id__in=data_ids)
                    .select_related('service_center')
                    .prefetch_related('reportsrecords_set')
                    .order_by('id'))
        
        # 3. Сериализация
        serializer = ReportFullSerializer(queryset, many=True)
        
        # 4. Ответ
        return Response({
            'success': True,
            'requested_count': len(data_ids),
            'returned_count': len(serializer.data),
            'results': serializer.data
        })


# ========================================== #
# 5. РАБОТА С АКТАМИ НРП
# ========================================== #

@extend_schema(
    tags=['Acts'],
    summary="Количество новых актов НРП после указанного id",
    description="Возвращает количество новых актов неремонтопригодности, имеющих ID более указанного.",
    parameters=[
        OpenApiParameter(
            name='after_id',
            description='Id c которого начинается поиск (число)',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY)
    ],
    responses={
        200: OpenApiResponse(
            description="Успешный ответ",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    'success_response',
                    value={'success': True, 'after_id': '105', 'count': 15},
                )
            ]
        ),
        400: OpenApiResponse(description="Ошибка валидации ID"),
        401: OpenApiResponse(description="Требуется авторизация")
    }
)
class ActsNewCountView(BasicAuthMixin, APIView):
    """Количество новых актов НРП после указанного id"""
    
    def get(self, request):
        validator = SingleIdValidationMixin()
        
        after_id, error_response = validator.get_and_validate_id(
            request, 
            param_name='after_id'
        )
        if error_response:
            return error_response
        
        count = NonRepairabilityAct.objects.filter(id__gt=after_id).count()
        
        return Response({
            'success': True,
            'after_id': request.GET.get('after_id'),
            'count': count
        })


@extend_schema(
    tags=['Acts'],
    summary="Получить данные новых актов НРП с пагинацией",
    description="Возвращает полные данные новых актов неремонтопригодности, которые были созданы после указанного ID. "
                "Поддерживает пагинацию для постраничного получения данных.",
    parameters=[
        OpenApiParameter(
            name='after_id',
            description='ID акта, после которого нужно получить данные',
            required=True,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='page',
            description='Номер страницы',
            required=False,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
        OpenApiParameter(
            name='page_size',
            description='Размер страницы (максимум 100, по умолчанию 50)',
            required=False,
            type=int,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
class ActsNewView(BasicAuthMixin, APIView):
    """Получить данные новых актов НРП после указанного ID с пагинацией"""
    
    serializer_class = NonRepairabilityActFullSerializer

    def get(self, request):
        # 1. Валидация after_id        
        validator = SingleIdValidationMixin()
        
        after_id, error_response = validator.get_and_validate_id(
            request, 
            param_name='after_id'
        )
        if error_response:
            return error_response

        # 2. Проверка существования акта
        if not NonRepairabilityAct.objects.filter(id=after_id).exists():
            return Response({
                'error': 'Not Found',
                'message': f'Act with id={after_id} does not exist'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # 3. Параметры пагинации
        page = request.GET.get('page', 1)
        page_size = request.GET.get('page_size', 50)
        
        try:
            page = int(page)
            page_size = int(page_size)
            if page_size > 100:
                page_size = 100
            if page_size < 1:
                page_size = 50
            if page < 1:
                page = 1
        except ValueError:
            page = 1
            page_size = 50
        
        # 4. Получаем queryset с оптимизацией связей и истории статусов
        queryset = (NonRepairabilityAct.objects
            .filter(id__gt=after_id)
            .select_related('center', 'product', 'model', 'code')
            .prefetch_related('statuses')
            .order_by('id'))
        
        # 5. Пагинация
        paginator = Paginator(queryset, page_size)
        
        if page > paginator.num_pages and paginator.num_pages > 0:
            return Response({
                'error': 'Not Found',
                'message': f'Page {page} does not exist. Total pages: {paginator.num_pages}'
            }, status=status.HTTP_404_NOT_FOUND)
        
        current_page = paginator.get_page(page)
        
        # 6. Сериализация
        serializer = NonRepairabilityActFullSerializer(current_page, many=True)
        
        # 7. Ответ
        return Response({
            'success': True,
            'after_id': after_id,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_pages': paginator.num_pages,
                'total_count': paginator.count
            },
            'results': serializer.data
        })


@extend_schema(
    tags=['Acts'],
    summary="Получить данные актов НРП по списку ID",
    description="Возвращает полные данные актов неремонтопригодности по переданному списку ID. "
                "Максимум 100 ID за запрос.",
    request={
        'application/json': {
            'type': 'object',
            'properties': {
                'ids': {
                    'type': 'array',
                    'items': {'type': 'integer'},
                    'example':[141, 142, 143, 144, 145],
                    'description': 'Список ID актов НРП (максимум 100)'
                }
            },
            'required': ['ids']
        }
    },
    responses={
        400: OpenApiResponse(description="Ошибка валидации формата JSON или превышен лимит ID"),
        401: OpenApiResponse(description="Требуется авторизация")
    }
)
class ActsByIdsView(BasicAuthMixin, APIView):
    """Получить данные актов НРП по списку ID"""
    
    serializer_class = NonRepairabilityActFullSerializer
    
    def post(self, request): 
        
        # 1. Валидация списка ID
        validator = JsonIdValidationMixin()
        data_ids, error_response = validator.get_and_validate_ids(request, max_limit=100)
        if error_response:
            return Response(error_response.data, status=error_response.status_code)
        
        # 2. Получаем queryset с оптимизацией
        queryset = (NonRepairabilityAct.objects
                    .filter(id__in=data_ids)
                    .select_related('center', 'product', 'model', 'code')
                    .prefetch_related('statuses')
                    .order_by('id'))
        
        # 3. Сериализация
        serializer = NonRepairabilityActFullSerializer(queryset, many=True)
        
        # 4. Ответ
        return Response({
            'success': True,
            'requested_count': len(data_ids),
            'returned_count': len(serializer.data),
            'results': serializer.data
        })
