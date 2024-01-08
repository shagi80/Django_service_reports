from django.urls import path, include
from .views import *


urlpatterns = [
    path('list/', ServiceCentersList.as_view(), name='centres_list_page'),
    path('add/', ServiceCentersAdd.as_view(), name='centres_add_page'),
    path('regions/', ServiceCentersRegionList.as_view(), name='centres_region_list_page'),
    path('update/<int:pk>/', ServiceCenterUpdate.as_view(), name='centres_update_page'),
    path('contacts-list/', ServiceCentersContactsList.as_view(), name='centres_contacts_page'),
    path('contact/<int:center_pk>/', ServiceCentersContactsByCenter.as_view(), name='centres_contact_page'),
    path('contact-add/', ServiceContactAdd.as_view(), name='contact_add_page'),
    path('contact-update/<int:pk>/', ServiceContactUpdate.as_view(), name='contact_update_page'),
    path('contact-delete/<int:contact_pk>/', ContactDelete, name='contact_delete_page'),
    path('export-list/', CentersListExport, name='export-list'),
]