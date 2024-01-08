""" формы докуметов """
from django import forms
from .models import ReportDocumnent, REPORT_DOCUMENT, RecordDocumnent


class ReportDocumentForm(forms.ModelForm):
    """ форма добавления документов отчета """

    class Meta:
        model = ReportDocumnent
        fields = '__all__'
        widgets = {
            'report' : forms.HiddenInput,
            'title' : forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'number' : forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'date' : forms.DateInput(format=('%Y-%m-%d'),
                                        attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control-file form-control-file-sm'}),
            }
        

class RecordDocumentForm(forms.ModelForm):
    """ форма добавления документов ремонта """

    class Meta:
        model = RecordDocumnent
        fields = '__all__'
        widgets = {
            'record' : forms.HiddenInput,
            'title' : forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'number' : forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'date' : forms.DateInput(format=('%Y-%m-%d'),
                                        attrs={'class': 'form-control form-control-sm', 'type': 'date'}),
            'file': forms.ClearableFileInput(attrs={'class': 'form-control-file form-control-file-sm'}),
            }

