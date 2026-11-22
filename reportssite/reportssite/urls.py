from functools import partial
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import path, include
from django.views.defaults import (
    server_error,
    page_not_found,
    permission_denied,
)
from rest_framework.permissions import AllowAny
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Замените 'new_api_app' на фактическое имя папки вашего нового приложения
from sales_api.urls import client_urlpatterns


handler403 = partial(permission_denied, template_name='errs/403.html')
handler404 = partial(page_not_found, template_name='errs/404.html')
handler500 = partial(server_error, template_name='errs/500.html')


# Оборачиваем клиентские маршруты в префикс 'api/b2b/' для корректной работы "Try it out" в Swagger
b2b_schema_patterns = [
    path('api/b2b/', include(client_urlpatterns)),
]


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('centres/', include('servicecentres.urls')),
    path('products/', include('products.urls')),
    path('reports/', include('reports.urls')),
    path('stat-reports/', include('stat_reports.urls')),
    path('upload/', include('upload.urls')),
    path('act/', include('non_repairability_act.urls')),
    
    # Внутреннее DRF API (1С)
    path('api/', include('api_1c.urls')),

    # Новое B2B API (замените 'new_api_app' на имя вашего нового приложения)
    path('api/b2b/', include('sales_api.urls')),

    # ==========================================================
    # ДОКУМЕНТАЦИЯ №1: Внутренняя (только для staff-персонала)
    # ==========================================================
    path(
        'api/schema/',
        staff_member_required(SpectacularAPIView.as_view()),
        name='schema'
    ),
    path(
        'api/schema/swagger-ui/',
        staff_member_required(SpectacularSwaggerView.as_view(url_name='schema')),
        name='swagger-ui'
    ),
    path(
        'api/schema/redoc/',
        staff_member_required(SpectacularRedocView.as_view(url_name='schema')),
        name='redoc'
    ),

    # ==========================================================
    # ДОКУМЕНТАЦИЯ №2: Внешняя для контрагентов (открытая)
    # ==========================================================
    path(
        'api/b2b/schema/',
        SpectacularAPIView.as_view(
            urlconf=b2b_schema_patterns,
            authentication_classes=[],
            permission_classes=[AllowAny],
            custom_settings={
                'TITLE': 'B2B Catalog API',
                'DESCRIPTION': 'Документация по работе с каталогом, ценами и остатками для контрагентов.',
                'VERSION': '1.0.0',
            }
        ),
        name='schema-b2b'
    ),
    path(
        'api/b2b/docs/',
        SpectacularSwaggerView.as_view(
            url_name='schema-b2b',
            authentication_classes=[],
            permission_classes=[AllowAny],
        ),
        name='swagger-b2b'
    ),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
