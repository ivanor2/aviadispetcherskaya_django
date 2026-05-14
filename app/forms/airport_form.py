from django import forms
import re

class AirportForm(forms.Form):
    icao_code = forms.CharField(
        max_length=4, min_length=2,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'UUSS', 'pattern': '[A-Z]{2,4}'}),
        label="ICAO код"
    )
    name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Шереметьево'}),
        label="Название аэропорта"
    )
    def clean_icao_code(self):
        code = self.cleaned_data.get('icao_code', '').upper()
        if not re.match(r'^[A-Z]{2,4}$', code):
            raise forms.ValidationError('ICAO-код должен состоять из 2-4 заглавных латинских букв')
        return code