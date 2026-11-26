from django.db.models import Q
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from rest_framework.generics import ListAPIView
from rest_framework.authentication import BasicAuthentication
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiExample, OpenApiResponse
from drf_spectacular.types import OpenApiTypes

from .models import GoodsItem, Price, Remnant, Storage, Group
from .permissions import IsCounterpartyEmployee
from .serializers import (
    StorageSerializer,
    GroupSerializer,
    GoodsItemSerializer,
    ItemRemnantSerializer,
    CatalogItemSerializer,
    PriceSerializer)
from .mixins import UpdatedAfterFilterMixin


class CustomPagination(PageNumberPagination):
    """Кастомная пагинация"""

    page_size = 100
    max_page_size = 1000
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,           # Общее количество товаров
            'total_pages': self.page.paginator.num_pages, # Общее количество страниц
            'current_page': self.page.number,             # Номер текущей страницы
            'has_next': self.page.has_next(),             # Флаг наличия следующей страницы (True/False)
            'results': data                               # Список товаров
        })


# ========================================== #
# 1. ПРОВЕРКА СВЯЗИ И АВТОРИЗАЦИИ
# ========================================== #

@extend_schema(
    tags=['Server'],
    summary="Проверка доступности API",
    description=(
        "Эндпоинт для проверки работоспособности и доступности сервера API (Health Check). "
        "Не требует передачи заголовков авторизации."
    ),
    auth=[],
    responses={
        200: OpenApiResponse(
            description="Сервер доступен и корректно обрабатывает запросы.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Успешный ответ',
                    value={'message': 'API is working'},
                    status_codes=['200'],
                )
            ]
        )
    }
)
class HealthCheckView(APIView):
    """Проверка доступности API"""
    
    authentication_classes = []
    permission_classes = [AllowAny]
    
    def get(self, request):
        return Response({'message': 'API is working'})


@extend_schema(
    tags=['Server'],
    summary="Проверка авторизации и получение контекста пользователя",
    description=(
        "Проверяет корректность учетных данных Basic Authentication и наличие привязки пользователя "
        "к активному контрагенту. Также доступен и для персонала сервиса."
        "Возвращает информацию о текущем пользователе, его организации-контрагенте, а также точное время "
        "и часовой пояс сервера (полезно для синхронизации меток времени `updated_after`)."
    ),
    responses={
        200: OpenApiResponse(
            description="Авторизация успешна, профиль пользователя привязан к контрагенту.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Успешная авторизация',
                    value={
                        'message': 'Authentication successful',
                        'user': 'ivanov_ii',
                        'counterparty': 'ООО "Ромашка"',
                        'server_time': '2026-11-21T18:50:00.123456+03:00',
                        'timestamp': 1795276200,
                        'timezone': 'Europe/Moscow',
                    },
                    status_codes=['200'],
                )
            ]
        ),
        401: OpenApiResponse(
            description="Ошибка аутентификации: не переданы учетные данные, неверный логин/пароль или некорректный заголовок Authorization.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверные учетные данные',
                    value={'detail': 'Invalid username/password.'},
                    status_codes=['401'],
                ),
                OpenApiExample(
                    name='Учетные данные не предоставлены',
                    value={'detail': 'Authentication credentials were not provided.'},
                    status_codes=['401'],
                ),
            ]
        ),
        403: OpenApiResponse(
            description="Доступ запрещен: пользователь успешно аутентифицирован, но не является сотрудником контрагента или персоналом сервиса.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Нет прав контрагента или персонала сервиса',
                    value={'detail': 'You do not have permission to perform this action.'},
                    status_codes=['403'],
                )
            ]
        ),
    }
)
class AuthTestView(APIView):
    """Проверка авторизации"""

    authentication_classes = [BasicAuthentication]
    permission_classes = [IsCounterpartyEmployee] 

    def get(self, request):
        now = timezone.now()
        company_name = None
        counterparty = request.counterparty
        if counterparty:
            company_name = counterparty.company_name
        return Response({
            'message': 'Authentication successful',
            'user': request.user.username,
            'counterparty': company_name,
            'server_time': now.isoformat(),
            'timestamp': int(now.timestamp()),
            'timezone': timezone.get_current_timezone_name()
        })


# ========================================== #
# 2. ПОЛУЧЕНИЕ СПРАВОЧНЫХ ДАННЫХ
# ========================================== #

@extend_schema(
    tags=['Catalog'],
    summary="Получение перечня складов",
    description=(
        "Возвращает постраничный справочник всех доступных складов компании с контактной информацией, "
        "адресами и графиком работы. Эндпоинт является публичным и не требует авторизации."
    ),
    auth=[],
    parameters=[
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Номер страницы для постраничного вывода (по умолчанию 1).',
            required=False,
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Количество записей на одной странице (по умолчанию 100, максимум 1000).',
            required=False,
        ),
    ],
    responses={
        200: OpenApiResponse(
            description="Успешное получение списка складов (с кастомной пагинацией).",
            response=StorageSerializer(many=True),
            examples=[
                OpenApiExample(
                    name='Список складов',
                    value={
                        'count': 2,
                        'total_pages': 1,
                        'current_page': 1,
                        'has_next': False,
                        'results': [
                            {
                                'code': '00-000001',
                                'name': 'Основной склад',
                                'city': 'Москва',
                                'addr': 'ул. Складская, д. 10, стр. 2',
                                'contact': '+7 (495) 123-45-67',
                                'work_time': 'Пн-Пт: 09:00 - 18:00',
                                'note': 'Въезд по пропускам',
                            },
                            {
                                'code': '00-000002',
                                'name': 'Склад Юг',
                                'city': 'Краснодар',
                                'addr': 'ул. Промышленная, д. 5',
                                'contact': '+7 (861) 987-65-43',
                                'work_time': 'Пн-Сб: 08:00 - 20:00',
                                'note': '',
                            }
                        ]
                    },
                    status_codes=['200'],
                )
            ]
        ),
        404: OpenApiResponse(
            description="Запрошена несуществующая страница пагинации.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверная страница',
                    value={'detail': 'Invalid page.'},
                    status_codes=['404'],
                )
            ]
        ),
    }
)
class StorageListAPIView(ListAPIView):
    queryset = Storage.objects.all()
    serializer_class = StorageSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    pagination_class = CustomPagination


@extend_schema(
    tags=['Catalog'],
    summary="Получение списка групп номенклатуры",
    description=(
        "Возвращает постраничный иерархический справочник групп (категорий) номенклатуры. "
        "Поддерживает инкрементальную выгрузку изменений с помощью параметра `updated_after`. "
        "Требует авторизации по протоколу Basic Auth."
    ),
    parameters=[
        OpenApiParameter(
            name='updated_after',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Нижняя граница инкрементальной выгрузки: вернуть группы, созданные или обновленные строго после "
                "указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:00:00Z` или `2026-11-18T15:00:00+03:00`)."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Номер страницы для постраничного вывода (по умолчанию 1).',
            required=False,
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Количество записей на одной странице (по умолчанию 100, максимум 1000).',
            required=False,
        ),
        OpenApiParameter(
            name='updated_to',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Верхняя граница инкрементальной выгрузки: вернуть записи, обновленные до или включительно "
                "до указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:05:00Z`). "
                "Рекомендуется передавать `server_time`, полученный перед началом цикла выгрузки."
            ),
            required=False,
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Успешное получение списка групп номенклатуры (с кастомной пагинацией).",
            response=GroupSerializer(many=True),
            examples=[
                OpenApiExample(
                    name='Список групп номенклатуры',
                    value={
                        'count': 2,
                        'total_pages': 1,
                        'current_page': 1,
                        'has_next': False,
                        'results': [
                            {
                                'code': 'GRP-001',
                                'owner_code': '',
                                'name': 'Электроинструмент',
                            },
                            {
                                'code': 'GRP-002',
                                'owner_code': 'GRP-001',
                                'name': 'Дрели и шуруповерты',
                            }
                        ]
                    },
                    status_codes=['200'],
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации параметров запроса (например, неверный формат даты в `updated_after`).",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверный формат даты',
                    value={
                        'updated_after': 'Неверный формат даты. Используйте ISO 8601 (например, 2026-11-18T12:00:00Z).'
                    },
                    status_codes=['400'],
                )
            ]
        ),
        401: OpenApiResponse(
            description="Ошибка аутентификации: не переданы или неверны учетные данные Basic Auth.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неавторизованный запрос',
                    value={'detail': 'Authentication credentials were not provided.'},
                    status_codes=['401'],
                )
            ]
        ),
        404: OpenApiResponse(
            description="Запрошена несуществующая страница пагинации.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверная страница',
                    value={'detail': 'Invalid page.'},
                    status_codes=['404'],
                )
            ]
        ),
    }
)
class GroupListAPIView(UpdatedAfterFilterMixin, ListAPIView):
    serializer_class = GroupSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
      
        # 1. Необязательный фильтр по дате обновления
        queryset = self.filter_by_updated_after(Group.objects.all())

        return queryset


@extend_schema(
    tags=['Catalog'],
    summary="Получение списка номенклатуры",
    description=(
        "Возвращает постраничный общий справочник товаров (номенклатуры) без привязки к персональным ценам и остаткам. "
        "Поддерживает инкрементальную выгрузку изменений по дате обновления (`updated_after`) и фильтрацию "
        "по родительской группе (`owner_code`). Для получения товаров в корне каталога (без родительской группы) "
        "передайте пустое значение `?owner_code=`. Требует авторизации по протоколу Basic Auth."
    ),
    parameters=[
        OpenApiParameter(
            name='updated_after',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Нижняя граница инкрементальной выгрузки: вернуть товары, обновленные строго после указанной даты и времени "
                "в формате ISO 8601 (например: `2026-11-18T12:00:00Z` или `2026-11-18T15:00:00+03:00`)."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='owner_code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                "Код родительской группы номенклатуры. Передайте пустую строку (`?owner_code=`), "
                "чтобы получить только корневые элементы без группы."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Номер страницы для постраничного вывода (по умолчанию 1).',
            required=False,
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Количество записей на одной странице (по умолчанию 100, максимум 1000).',
            required=False,
        ),
         OpenApiParameter(
            name='updated_to',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Верхняя граница инкрементальной выгрузки: вернуть записи, обновленные до или включительно "
                "до указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:05:00Z`). "
                "Рекомендуется передавать `server_time`, полученный перед началом цикла выгрузки."
            ),
            required=False,
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Успешное получение списка номенклатуры (с кастомной пагинацией).",
            response=GoodsItemSerializer(many=True),
            examples=[
                OpenApiExample(
                    name='Список номенклатуры',
                    value={
                        'count': 2,
                        'total_pages': 1,
                        'current_page': 1,
                        'has_next': False,
                        'results': [
                            {
                                'code': '00-000105',
                                'owner_code': 'GRP-002',
                                'name': 'Дрель-шуруповерт аккумуляторная 18В',
                                'unit_code': '796',
                                'unit_name': 'шт',
                            },
                            {
                                'code': '00-000106',
                                'owner_code': 'GRP-002',
                                'name': 'Набор бит 32 предмета',
                                'unit_code': '778',
                                'unit_name': 'упак',
                            }
                        ]
                    },
                    status_codes=['200'],
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации параметров запроса (например, неверный формат даты в `updated_after`).",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверный формат даты',
                    value={
                        'updated_after': 'Неверный формат даты. Используйте ISO 8601 (например, 2026-11-18T12:00:00Z).'
                    },
                    status_codes=['400'],
                )
            ]
        ),
        401: OpenApiResponse(
            description="Ошибка аутентификации: не переданы или неверны учетные данные Basic Auth.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неавторизованный запрос',
                    value={'detail': 'Authentication credentials were not provided.'},
                    status_codes=['401'],
                )
            ]
        ),
        404: OpenApiResponse(
            description="Запрошена несуществующая страница пагинации.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверная страница',
                    value={'detail': 'Invalid page.'},
                    status_codes=['404'],
                )
            ]
        ),
    }
)
class GoodsItemListAPIView(UpdatedAfterFilterMixin, ListAPIView):
    serializer_class = GoodsItemSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):

        # 1. Необязательный фильтр по дате обновления
        queryset = self.filter_by_updated_after(GoodsItem.objects.all())

        # 2. Необязательный фильтр по родительской группе
        owner_code = self.request.query_params.get('owner_code')
        if owner_code is not None:
            # Используем is not None, чтобы можно было передать ?owner_code= для товаров в корне (без группы)
            queryset = queryset.filter(owner_code=owner_code)

        return queryset


# ========================================== #
# 3. ПОЛУЧЕНИЕ ОСТАТКОВ И ЦЕН
# ========================================== #

@extend_schema(
    tags=['Catalog'],
    summary="Получение остатков по конкретному складу",
    description=(
        "Возвращает постраничный плоский список актуальных остатков товаров по указанному складу. "
        "Параметр `storage_code` является обязательным. Поддерживает инкрементальную выгрузку "
        "изменений остатков по дате и времени (`updated_after`). Требует авторизации по протоколу Basic Auth."
    ),
    parameters=[
        OpenApiParameter(
            name='storage_code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description='Код склада, по которому запрашиваются остатки (обязательный параметр).',
            required=True,
        ),
        OpenApiParameter(
            name='updated_after',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Нижняя граница инкрементальной выгрузки: вернуть записи об остатках, обновленные строго после "
                "указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:00:00Z` или `2026-11-18T15:00:00+03:00`)."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Номер страницы для постраничного вывода (по умолчанию 1).',
            required=False,
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Количество записей на одной странице (по умолчанию 100, максимум 1000).',
            required=False,
        ),
         OpenApiParameter(
            name='updated_to',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Верхняя граница инкрементальной выгрузки: вернуть записи, обновленные до или включительно "
                "до указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:05:00Z`). "
                "Рекомендуется передавать `server_time`, полученный перед началом цикла выгрузки."
            ),
            required=False,
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Успешное получение списка остатков по складу (с кастомной пагинацией).",
            response=ItemRemnantSerializer(many=True),
            examples=[
                OpenApiExample(
                    name='Список остатков по складу',
                    value={
                        'count': 2,
                        'total_pages': 1,
                        'current_page': 1,
                        'has_next': False,
                        'results': [
                            {
                                'storage_code': '00-000001',
                                'item_code': '00-000105',
                                'count': 15.0,
                            },
                            {
                                'storage_code': '00-000001',
                                'item_code': '00-000106',
                                'count': 0.0,
                            }
                        ]
                    },
                    status_codes=['200'],
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации: не передан обязательный параметр `storage_code` или указан неверный формат даты в `updated_after`.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Отсутствует storage_code',
                    value={
                        'storage_code': 'Обязательный параметр запроса.'
                    },
                    status_codes=['400'],
                ),
                OpenApiExample(
                    name='Неверный формат даты',
                    value={
                        'updated_after': 'Неверный формат даты. Используйте ISO 8601 (например, 2026-11-18T12:00:00Z).'
                    },
                    status_codes=['400'],
                ),
            ]
        ),
        401: OpenApiResponse(
            description="Ошибка аутентификации: не переданы или неверны учетные данные Basic Auth.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неавторизованный запрос',
                    value={'detail': 'Authentication credentials were not provided.'},
                    status_codes=['401'],
                )
            ]
        ),
        404: OpenApiResponse(
            description="Запрошена несуществующая страница пагинации.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверная страница',
                    value={'detail': 'Invalid page.'},
                    status_codes=['404'],
                )
            ]
        ),
    }
)
class RemnantListAPIView(UpdatedAfterFilterMixin, ListAPIView):
    serializer_class = ItemRemnantSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    def get_queryset(self):
        storage_code = self.request.query_params.get('storage_code')
        if not storage_code:
            raise ValidationError({
                'storage_code': 'Обязательный параметр запроса.'
            })

        queryset = Remnant.objects.filter(storage_code=storage_code)
        queryset = self.filter_by_updated_after(queryset)

        return queryset


@extend_schema(
    tags=['Catalog'],
    summary="Получение персонального каталога с ценами и остатками",
    description=(
        "Возвращает постраничный каталог товаров, доступных текущему контрагенту (только позиции, "
        "на которые у контрагента назначена персональная цена), с актуальными ценами и остатками "
        "по указанному складу. Могут быть отобраны только положительные остатки.\n\n"
        "**Особенности фильтрации:**\n"
        "- `storage_code` - обязательно поле - код склада для выборки остатков.\n"
        "- `in_stock` - при `true` возвращает товары с положительным остатком, при `false` (отсутствии параметра)"
        " — все товары.\n"
        "- `updated_after` - нижняя граница инкрементной выгрузки. Возвращает товар, если после указанной даты "
        "изменилась сама карточка номенклатуры, персональная цена контрагента или остаток товара.\n"
        "- `updated_to` - верхняя граница инкрементной выгрузки. Возвращает товар, его карточка, персональная "
        "цена контрагента или остаток изменились до или включая указанную дату.\n"
        "- Результаты детерминированно отсортированы по `name`, затем по `code`."
    ),
    parameters=[
        OpenApiParameter(
            name='updated_after',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Нижняя граница инкрементальной выгрузки: вернуть записи, обновленные строго после "
                "указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:00:00Z` или `2026-11-18T15:00:00+03:00`)."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='owner_code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                "Код родительской группы номенклатуры. Передача `?owner_code=` "
                "позволяет получить товары из корневого узла структуры номенклатуры."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='storage_code',
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description=(
                "Код склада для отбора остатков."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='in_stock',
            type=OpenApiTypes.BOOL,
            location=OpenApiParameter.QUERY,
            description=(
                "Фильтр по наличию остатков: `true` — только товары с остатком > 0,"
                "`false` (или отсутствие парметра) — все товары."
            ),
            required=False,
        ),
        OpenApiParameter(
            name='page',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Номер страницы для постраничного вывода (по умолчанию 1).',
            required=False,
        ),
        OpenApiParameter(
            name='page_size',
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description='Количество записей на одной странице (по умолчанию 100, максимум 1000).',
            required=False,
        ),
         OpenApiParameter(
            name='updated_to',
            type=OpenApiTypes.DATETIME,
            location=OpenApiParameter.QUERY,
            description=(
                "Верхняя граница инкрементальной выгрузки: вернуть записи, обновленные до или включительно "
                "до указанной даты и времени в формате ISO 8601 (например: `2026-11-18T12:05:00Z`). "
                "Рекомендуется передавать `server_time`, полученный перед началом цикла выгрузки."
            ),
            required=False,
        )
    ],
    responses={
        200: OpenApiResponse(
            description="Успешное получение персонального каталога контрагента (с кастомной пагинацией).",
            response=CatalogItemSerializer(many=True),
            examples=[
                OpenApiExample(
                    name='Персональный каталог с ценами и остатками',
                    value={
                        'count': 2,
                        'total_pages': 1,
                        'current_page': 1,
                        'has_next': False,
                        'results': [
                            {
                                'code': '00-000105',
                                'owner_code': 'GRP-002',
                                'name': 'Дрель-шуруповерт аккумуляторная 18В',
                                'unit_code': '796',
                                'unit_name': 'шт',
                                'price': '8450.00',
                                'remnants': [
                                    {
                                        'storage_code': '00-000001',
                                        'storage_name': 'Основной склад',
                                        'count': 15.0,
                                    },
                                    {
                                        'storage_code': '00-000002',
                                        'storage_name': 'Склад Юг',
                                        'count': 4.0,
                                    }
                                ]
                            },
                            {
                                'code': '00-000106',
                                'owner_code': 'GRP-002',
                                'name': 'Набор бит 32 предмета',
                                'unit_code': '778',
                                'unit_name': 'упак',
                                'price': '1200.00',
                                'remnants': []
                            }
                        ]
                    },
                    status_codes=['200'],
                )
            ]
        ),
        400: OpenApiResponse(
            description="Ошибка валидации параметров запроса или отсутствие привязки пользователя к контрагенту.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверное булево значение in_stock',
                    value={
                        'in_stock': 'Неверное булево значение. Используйте true или false.'
                    },
                    status_codes=['400'],
                ),
                OpenApiExample(
                    name='Неверный формат даты updated_after',
                    value={
                        'updated_after': 'Неверный формат даты. Используйте ISO 8601 (например, 2026-11-18T12:00:00Z).'
                    },
                    status_codes=['400'],
                ),
                OpenApiExample(
                    name='Профиль не привязан к контрагенту',
                    value={
                        'message': 'Профиль пользователя не привязан к контрагенту.'
                    },
                    status_codes=['400'],
                ),
            ]
        ),
        401: OpenApiResponse(
            description="Ошибка аутентификации: не переданы или неверны учетные данные Basic Auth.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неавторизованный запрос',
                    value={'detail': 'Authentication credentials were not provided.'},
                    status_codes=['401'],
                )
            ]
        ),
        403: OpenApiResponse(
            description="Доступ запрещен: пользователь не является сотрудником контрагента (не пройден пермишен IsCounterpartyEmployee).",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Нет прав контрагента',
                    value={'detail': 'You do not have permission to perform this action.'},
                    status_codes=['403'],
                )
            ]
        ),
        404: OpenApiResponse(
            description="Запрошена несуществующая страница пагинации.",
            response=OpenApiTypes.OBJECT,
            examples=[
                OpenApiExample(
                    name='Неверная страница',
                    value={'detail': 'Invalid page.'},
                    status_codes=['404'],
                )
            ]
        ),
    }
)
class CatalogExportAPIView(UpdatedAfterFilterMixin, ListAPIView):
    serializer_class = CatalogItemSerializer
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsCounterpartyEmployee]
    pagination_class = CustomPagination

    def get_queryset(self):
        counterparty = self.request.counterparty

        if not counterparty:
            raise ValidationError({
                'message': 'Профиль пользователя не привязан к контрагенту.'
            })

        # 1. Базовый отбор: получаем коды всех товаров, на которые у контрагента назначена цена.
        priced_item_codes = Price.objects.filter(
            counterparty_code=counterparty.code
        ).values_list('item_code', flat=True)

        queryset = GoodsItem.objects.filter(code__in=priced_item_codes)

        # 2. Необязательный фильтр по родительской группе (?owner_code=)
        owner_code = self.request.query_params.get('owner_code')
        if owner_code is not None:
            queryset = queryset.filter(owner_code=owner_code)

        # Читаем код склада заранее, так как он влияет и на фильтр наличия (in_stock),
        # и на отслеживание изменений остатков (updated_after / updated_to)
        storage_code = self.request.query_params.get('storage_code')

        # 3. Необязательный фильтр по наличию остатков (?in_stock=true / ?in_stock=false)
        in_stock_param = self.request.query_params.get('in_stock')
        if in_stock_param is not None:
            bool_field = serializers.BooleanField()
            try:
                in_stock = bool_field.to_internal_value(in_stock_param)
            except serializers.ValidationError:
                raise ValidationError({
                    'in_stock': 'Неверное булево значение. Используйте true или false.'
                })

            # Фильтруем только при in_stock=True; при False (как и без параметра) отдаем все позиции с ценами
            if in_stock:
                remnants_filter = Remnant.objects.filter(count__gt=0)
                if storage_code:
                    remnants_filter = remnants_filter.filter(storage_code=storage_code)

                available_item_codes = remnants_filter.values_list('item_code', flat=True)
                queryset = queryset.filter(code__in=available_item_codes)

        # 4. Комплексный фильтр инкрементальной выгрузки (?updated_after= и ?updated_to=)
        updated_after, updated_to = self.get_updated_range()

        if updated_after is not None or updated_to is not None:
            item_time_q = Q()
            price_qs = Price.objects.filter(counterparty_code=counterparty.code)
            remnant_qs = Remnant.objects.all()

            if storage_code:
                remnant_qs = remnant_qs.filter(storage_code=storage_code)

            if updated_after is not None:
                item_time_q &= Q(updated_at__gt=updated_after)
                price_qs = price_qs.filter(updated_at__gt=updated_after)
                remnant_qs = remnant_qs.filter(updated_at__gt=updated_after)

            if updated_to is not None:
                item_time_q &= Q(updated_at__lte=updated_to)
                price_qs = price_qs.filter(updated_at__lte=updated_to)
                remnant_qs = remnant_qs.filter(updated_at__lte=updated_to)

            # А) Товары, у которых обновилась персональная цена этого контрагента
            updated_price_codes = price_qs.values_list('item_code', flat=True)

            # Б) Товары, у которых изменился остаток (если передан storage_code — отслеживаем только этот склад)
            updated_remnant_codes = remnant_qs.values_list('item_code', flat=True)

            # В) Объединяем условия: изменилась карточка ИЛИ цена ИЛИ остаток
            queryset = queryset.filter(
                item_time_q |
                Q(code__in=updated_price_codes) |
                Q(code__in=updated_remnant_codes)
            )

        # Обязательная детерминированная сортировка для стабильной работы пагинации
        return queryset.order_by('name', 'code')

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page_items = self.paginate_queryset(queryset)

        items_to_serialize = page_items if page_items is not None else queryset
        page_codes = [item.code for item in items_to_serialize]

        # Загружаем цены для товаров текущей страницы
        prices_map = dict(
            Price.objects.filter(
                counterparty_code=request.counterparty.code,
                item_code__in=page_codes
            ).values_list('item_code', 'price')
        )

        # Загружаем справочник названий складов
        storages_map = dict(Storage.objects.values_list('code', 'name'))

        # Загружаем положительные остатки для товаров текущей страницы
        remnants_qs = Remnant.objects.filter(item_code__in=page_codes, count__gt=0)

        # Если передан фильтр по конкретному складу, отдаем в массиве remnants данные только по нему
        storage_code = request.query_params.get('storage_code')
        if storage_code:
            remnants_qs = remnants_qs.filter(storage_code=storage_code)

        remnants_map = {}
        for r in remnants_qs:
            remnants_map.setdefault(r.item_code, []).append({
                'storage_code': r.storage_code,
                'storage_name': storages_map.get(r.storage_code, r.storage_code),
                'count': r.count
            })

        context = self.get_serializer_context()
        context['prices_map'] = prices_map
        context['remnants_map'] = remnants_map

        serializer = self.get_serializer(items_to_serialize, many=True, context=context)

        if page_items is not None:
            return self.get_paginated_response(serializer.data)

        return Response(serializer.data)

# ========================================== #
# 4. ЗАПИСЬ
# ========================================== #

class BulkUpsertAPIView(APIView):
    """
    Базовый класс для массовой загрузки и обновления (Upsert) данных из 1С.
    Принимает JSON-массив объектов, валидирует через сериализатор и выполняет bulk_create
    с обновлением существующих записей при совпадении уникальных ключей.
    """
    authentication_classes = [BasicAuthentication]
    permission_classes = [IsAdminUser]  # Запись разрешена только сервисным учеткам / администраторам

    model = None
    serializer_class = None
    unique_fields = []
    update_fields = []
    has_updated_at = False
    sum_double = False
    sum_field = 'count'

    def post(self, request):
        # 1. Валидируем входящий JSON-массив целиком
        serializer = self.serializer_class(data=request.data, many=True)
        serializer.is_valid(raise_exception=True)

        validated_data = serializer.validated_data
        if not validated_data:
            return Response(
                {'status': 'ok', 'processed': 0},
                status=status.HTTP_200_OK
            )

        # 2. Защита от дублей внутри одного пакета по unique_fields
        if self.unique_fields:
            deduped = {}
            for item in validated_data:
                key = tuple(item.get(field) for field in self.unique_fields)
                if key in deduped and self.sum_double:
                    current_val = deduped[key].get(self.sum_field) or 0
                    new_val = item.get(self.sum_field) or 0
                    deduped[key].update(item)
                    deduped[key][self.sum_field] = current_val + new_val
                else:
                    deduped[key] = item
            validated_data = list(deduped.values())

        now = timezone.now()
        instances = []

        # 3. Формируем экземпляры моделей в памяти без обращения к БД
        for item in validated_data:
            if self.has_updated_at:
                # Принудительно обновляем метку времени, т.к. bulk_create не вызывает auto_now=True
                item['updated_at'] = now
            instances.append(self.model(**item))

        # 4. Формируем итоговый список обновляемых полей
        fields_to_update = list(self.update_fields)
        if self.has_updated_at and 'updated_at' not in fields_to_update:
            fields_to_update.append('updated_at')

        # 5. Выполняем массовую вставку / обновление одним пакетом (по 200 записей на запрос)
        self.model.objects.bulk_create(
            instances,
            batch_size=200,
            update_conflicts=True,
            unique_fields=self.unique_fields,
            update_fields=fields_to_update,
        )

        return Response(
            {'status': 'ok', 'processed': len(instances)},
            status=status.HTTP_200_OK
        )


@extend_schema(
    tags=['Import (1C)'],
    summary="Массовая загрузка и обновление складов",
    request=StorageSerializer(many=True),
)
class StorageBulkImportAPIView(BulkUpsertAPIView):
    model = Storage
    serializer_class = StorageSerializer
    unique_fields = ['code']
    update_fields = ['name', 'city', 'addr', 'contact', 'work_time', 'note']
    has_updated_at = True


@extend_schema(
    tags=['Import (1C)'],
    summary="Массовая загрузка и обновление групп номенклатуры",
    request=GroupSerializer(many=True),
)
class GroupBulkImportAPIView(BulkUpsertAPIView):
    model = Group
    serializer_class = GroupSerializer
    unique_fields = ['code']
    update_fields = ['owner_code', 'name']
    has_updated_at = True


@extend_schema(
    tags=['Import (1C)'],
    summary="Массовая загрузка и обновление номенклатуры",
    request=GoodsItemSerializer(many=True),
)
class GoodsItemBulkImportAPIView(BulkUpsertAPIView):
    model = GoodsItem
    serializer_class = GoodsItemSerializer
    unique_fields = ['code']
    update_fields = ['owner_code', 'name', 'unit_code', 'unit_name']
    has_updated_at = True


@extend_schema(
    tags=['Import (1C)'],
    summary="Массовая загрузка и обновление остатков",
    request=ItemRemnantSerializer(many=True),
)
class RemnantBulkImportAPIView(BulkUpsertAPIView):
    model = Remnant
    serializer_class = ItemRemnantSerializer
    unique_fields = ['storage_code', 'item_code']
    update_fields = ['count']
    has_updated_at = True
    sum_double = True


@extend_schema(
    tags=['Import (1C)'],
    summary="Массовая загрузка и обновление цен контрагентов",
    request=PriceSerializer(many=True),
)
class PriceBulkImportAPIView(BulkUpsertAPIView):
    model = Price
    serializer_class = PriceSerializer
    unique_fields = ['counterparty_code', 'item_code']
    update_fields = ['price']
    has_updated_at = True
