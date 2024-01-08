from django.urls import path, re_path
from .views import *

urlpatterns = [
    path('report-export/<int:report_pk>', export_report_xls, name='report_export'),
    path('reports-list/', ReportsForStaff.as_view(), name='reports_list'),
    path('reports-user-list/', ReportsForUser.as_view(), name='reports_user_list'),
    path('report-change-status/', ReportChangeStatus, name='report-change-status'),
    path('report-add/', ReportAdd, name='report-add'),
    path('report-update/<int:report_pk>', ReportUpdate, name='report-update'),
    path('report-send/', ReportSend, name='report-send'),
    path('report-change-status/', ReportChangeStatus, name='report-change-status'),
    path('report/<int:pk>', ReportDetail.as_view(), name='report_page'),
    path('report-delete/<int:report_pk>', ReportDelete, name='report_delete'),
    path('report-can-send/', ReportCanSend, name='report_can_send'),

    # ремонт, работа менеджера
    path('record-for-staff/<int:pk>', RecordForStaff.as_view(), name='record-for-staff'),
    path('record-add-memder/', AddRecordMember, name='record-add-member'),
    path('record-delete-memder/', DeleteRecordMember, name='record-delete-member'),
    path('record-delete remark/', DeleteRecordRemark, name='record-delete-remark'),
    path('record-verified/', RecordVerified, name='record-verified'),
    path('record-cancel-verified/', RecordCancelVerified, name='record-cancel-verified'),
    path('record-delete-staff/', RecordDeleteStaff, name='record-delete-staff'),
    path('record-part-delete-staff/', RecordPartStaffDelete, name='record-part-delete-staff'),
    # ремонт, работа пользователя
    path('record-add/<int:report_pk>', RecordAdd.as_view(), name='record_add_page'),
    path('record-update/<int:pk>', RecordUpdate.as_view(), name='record_update_page'),
    path('record-delete/<int:report_pk>', RecordDelete, name='record_delete'),
    path('record-copy/', RecordCopy, name='record-copy'),
    path('record-remove/', RecordRemove, name='record-remove'),
    

    path('ajax/codes-load/', load_codes_data, name='ajax_load_codes'),
    path('ajax/models-load/', load_models_data, name='ajax_load_models'),
    path('ajax/work-price-load/', load_work_price_data, name='ajax_load_work-price'),

    path('user-ordered-parts/', OrderedParts.as_view(), name='ordered-parts'),
    path('staff-ordered-parts/', StaffOrderedParts.as_view(), name='staff-ordered-parts'),
    path('send-parts/', SendParts, name='send-parts'),    
    path('parts-to-xls/<int:center_pk>', ExportPartsToXLS.as_view(), name='parts-to-xls'),
    path('accept-all/', accept_all, name='accept-all'),
    path('get-record-data/', getRecordData, name='get-record-data'),

]
