from django import forms
import re

class AirlineForm(forms.Form):
    code = forms.CharField(
        max_length=3, min_length=3,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ABC', 'pattern': '[A-Z]{3}'}),
        label="Код авиакомпании (3 буквы)"
    )
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название'}),
        label="Название"
    )
    def clean_code(self):
        code = self.cleaned_data.get('code', '').upper()
        if not re.match(r'^[A-Z]{3}$', code):
            raise forms.ValidationError('Код должен состоять ровно из 3 заглавных латинских букв')
        return code