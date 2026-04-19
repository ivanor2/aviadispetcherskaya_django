from django import forms
from app.models import Airport
import re


class AirportForm(forms.ModelForm):
    """Форма добавления/редактирования аэропорта"""

    class Meta:
        model = Airport
        fields = ['icao_code', 'name', 'country', 'city']

    def clean_icao_code(self):
        """Валидация ICAO-кода: ровно 4 буквы латиницы"""
        code = self.cleaned_data.get('icao_code', '').upper()
        if not re.match(r'^[A-Z]{4}$', code):
            raise forms.ValidationError(
                'ICAO-код должен состоять из 4 букв латиницы'
            )
        return code