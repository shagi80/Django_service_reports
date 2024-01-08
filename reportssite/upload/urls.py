""" upload urls """
from django.urls import path
from .views import AddReportDocumet, DeleteReportDocumet, AddRecordDocumet, DeleteRecordDocumet

urlpatterns = [
    path('report-document-upload/<int:report_pk>', AddReportDocumet, name='report-document-upload'),
    path('report-document-delete/<int:report_pk>', DeleteReportDocumet, name='report-document-delete'),
    path('record-document-upload/<int:record_pk>', AddRecordDocumet, name='record-document-upload'),
    path('record-document-delete/<int:record_pk>', DeleteRecordDocumet, name='record-document-delete'),
]