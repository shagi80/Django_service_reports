from django.urls import path
from .views import (
    HealthCheckView,
    AuthTestView,
    ServerTimeView,
    ChangeLogsCountView,
    ReportsNewView,
    ReportsByIdsView,
    ServiceContactDetailView,
    ServiceRegionsDetailView,
    ServiceCentersDetailView,
    MainProductDetailView,
    ModelDetailView,
    CodeDetailView,
    ChangeLogsDateRangeView,
    ReportsNewCountView,
    ActsNewCountView,
    ActsByIdsView,
    ActsNewView
)


urlpatterns = [
    # Health & Auth
    path('health/', HealthCheckView.as_view(), name='health_check'),
    path('auth-test/', AuthTestView.as_view(), name='auth_test'),
    path('server-time/', ServerTimeView.as_view(), name='server_time'),
    
    # Change Logs
    path('changelogs/count/', ChangeLogsCountView.as_view(), name='changelogs_count'),
    path('changelogs/daterange/', ChangeLogsDateRangeView.as_view(), name='changelogs_daterange'),
    
    # Entities
    path('models/ServiceRegions/', ServiceRegionsDetailView.as_view(), name='service_region'),
    path('models/ServiceCenters/', ServiceCentersDetailView.as_view(), name='service_center'),
    path('models/ServiceContacts/', ServiceContactDetailView.as_view(), name='service_contact'),
    path('models/MainProducts/', MainProductDetailView.as_view(), name='mainproduct'),
    path('models/Models/', ModelDetailView.as_view(), name='model'),
    path('models/Codes/', CodeDetailView.as_view(), name='code'),

    # Reports
    path('reports/new-count/', ReportsNewCountView.as_view(), name='reports_new_count'),
    path('reports/data-new/', ReportsNewView.as_view(), name='reports_data_new'),
    path('reports/data-ids/', ReportsByIdsView.as_view(), name='reports_data_ids'),

    # Acts
    path('acts/new-count/', ActsNewCountView.as_view(), name='acts_new_count'),
    path('acts/data-new/', ActsNewView.as_view(), name='acts_data_new'),
    path('acts/data-ids/', ActsByIdsView.as_view(), name='acts_data_ids'),

]