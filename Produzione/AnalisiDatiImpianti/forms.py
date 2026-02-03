from django import forms

class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'

class GeneraReportForm(forms.Form):
    datetime_start = forms.DateTimeField(required=True, label='Inizio', widget=DateTimeInput(),help_text="Scegliere giorno e ora inizio")
    datetime_end = forms.DateTimeField(required=True, label='Fine', widget=DateTimeInput(), help_text="Scegliere giorno e ora fine")
    impianto = forms.CharField(required=True,)

