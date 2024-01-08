from functools import partial
from django.conf.urls.static import static
from django.conf import settings
from django.contrib import admin
from django.urls import path, include
from django.views.defaults import server_error, page_not_found, permission_denied


handler403 = partial(permission_denied, template_name='errs/403.html')
handler404 = partial(page_not_found, template_name='errs/404.html')
handler500 = partial(server_error, template_name='errs/500.html')


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('main.urls')),
    path('centres/', include('servicecentres.urls')),
    path('products/', include('products.urls')),
    path('reports/', include('reports.urls')),
    path('stat-reports/', include('stat_reports.urls')),
    path('upload/', include('upload.urls')),
    path('act/', include('non_repairability_act.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)



