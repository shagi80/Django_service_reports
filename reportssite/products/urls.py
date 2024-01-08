from django.urls import path, include
from .views import *


urlpatterns = [
    path('list/', ProductsList.as_view(), name='products_list_page'),
    path('code_and_prices-list', CodeAndPriceList.as_view(), name='code_and_prices_page'),
    path('code_and_prices-list/<int:center_pk>', CodeAndPriceList.as_view(), name='code_and_prices_page'),
    path('code-add/', CodesAdd.as_view(), name='code_add_page'),
    path('code-update/<int:pk>', CodesUpdate.as_view(), name='code_update_page'),

    path('price-add/', BasePriceAdd.as_view(), name='price_add_page'),
    path('price-add/<int:code_pk>', BasePriceAdd.as_view(), name='price_add_page'),
    path('price-add/<str:price_type>', BasePriceAdd.as_view(), name='price_add_page'),
    path('prices-list/<str:price_type>', BasePriceList.as_view(), name='prices_list_page'),
    path('price-update/<int:pk>', BasePriceUpdate.as_view(), name='price_update_page'),
    path('price-delete/<int:price_pk>', BasePriceDelete, name='price_delete_page'),

    path('centerprices-list/<int:code_pk>', CodePricesPage.as_view(), name='code_prices_page'),
    path('centerprice-add/', CenterPriceAdd.as_view(), name='centerprice_add_page'),
    path('centerprice-add/<int:code_pk>', CenterPriceAdd.as_view(), name='centerprice_add_page'),
    path('centerprice-add/<int:code_pk>/<int:center_pk>', CenterPriceAdd.as_view(), name='centerprice_add_page'),
    path('centerprice-update/<int:pk>', CenterPriceUpdate.as_view(), name='centerprice_update_page'),
    path('ajax/price-load-groups/', load_groups, name='ajax_load_groups'),
    path('centerprice-delete/<int:price_pk>', CenterPriceDelete, name='centerprice_delete_page'),
    

]
