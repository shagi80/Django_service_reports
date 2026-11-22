from django.urls import path

from .views import (
    HealthCheckView,
    AuthTestView,
    StorageListAPIView,
    GroupListAPIView,
    GoodsItemListAPIView,
    RemnantListAPIView,
    CatalogExportAPIView,
    StorageBulkImportAPIView,
    GroupBulkImportAPIView,
    GoodsItemBulkImportAPIView,
    RemnantBulkImportAPIView,
    PriceBulkImportAPIView,
)

# 1. Эндпоинты для контрагентов (попадут в документацию для клиентов)
client_urlpatterns = [
    path('health/', HealthCheckView.as_view(), name='health-check'),
    path('auth-test/', AuthTestView.as_view(), name='auth-test'),
    path('storages/', StorageListAPIView.as_view(), name='storage-list'),
    path('groups/', GroupListAPIView.as_view(), name='group-list'),
    path('goods/', GoodsItemListAPIView.as_view(), name='goods-list'),
    path('remnants/', RemnantListAPIView.as_view(), name='remnant-list'),
    path('catalog/', CatalogExportAPIView.as_view(), name='catalog-export'),
]

# 2. Служебные эндпоинты загрузки из 1С (только для staff, не видны контрагентам)
import_urlpatterns = [
    path('import/storages/', StorageBulkImportAPIView.as_view(), name='storage-bulk-import'),
    path('import/groups/', GroupBulkImportAPIView.as_view(), name='group-bulk-import'),
    path('import/goods/', GoodsItemBulkImportAPIView.as_view(), name='goods-bulk-import'),
    path('import/remnants/', RemnantBulkImportAPIView.as_view(), name='remnant-bulk-import'),
    path('import/prices/', PriceBulkImportAPIView.as_view(), name='price-bulk-import'),
]

urlpatterns = client_urlpatterns + import_urlpatterns
