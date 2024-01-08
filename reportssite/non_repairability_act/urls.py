from django.urls import path

from . import views

urlpatterns = [
    path('list/', views.ActListView.as_view(), name='act-list'),
    path('user/create/', views.ActCreateView.as_view(),name='act-create'),
    path('user/update/<int:pk>/', views.ActUpdateView.as_view(), name='act-user-update'),
    path('user/delete/<int:pk>/', views.ActDeleteView.as_view(), name='act-user-delete'),
    path('user/get-models/', views.GetModelView.as_view(), name='act-get-models'),
    path('user/get-codes/', views.GetCodeView.as_view(), name='act-get-codes'),
    path('user/del-file/', views.DelFileView.as_view(), name='act-del-file'),

    path('staff/detail/<int:pk>/', views.ActDeatailForStaffView.as_view(), name='act-staff-detail'),
    path('staff/delete/<int:pk>/', views.ActDeleteView.as_view(), name='act-staff-delete'),
    path('staff/status/change/', views.ActStaffChangeStatusView.as_view(), name='act-staff-change-status'),
    path('staff/member/add/', views.ActAddMemberView.as_view(), name='act-staff-add-member'),
    path('staff/member/delete/', views.ActDeleteMemberView.as_view(), name='act-delete-member'),
    path('staff/user-member/delete/', views.ActDeleteUserMemberView.as_view(), name='act-delete-user-member'),
    
    path('print/<int:pk>', views.download_pdf, name='act-download'),
    path('check/<int:pk>/', views.ActDetailCheckView.as_view(), name='act-check'),
]
