# app/forms/flight_form.py
from django import forms
from app.models import Flight, Airport
import re

class FlightForm(forms.ModelForm):
    """Форма создания/редактирования рейса"""
    class Meta:
        model = Flight
        fields = [
            'flight_number', 'airline_name',
            'departure_airport', 'arrival_airport',
            'departure_date', 'departure_time',
            'total_seats', 'free_seats'
        ]
        widgets = {
            'departure_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'departure_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'flight_number': forms.TextInput(attrs={'class': 'form-control'}),
            'airline_name': forms.TextInput(attrs={'class': 'form-control'}),
            'total_seats': forms.NumberInput(attrs={'class': 'form-control'}),
            'free_seats': forms.NumberInput(attrs={'class': 'form-control'}),
            'departure_airport': forms.Select(attrs={'class': 'form-select'}),
            'arrival_airport': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Если это не создание, а редактирование, можно отключить некоторые поля
        if self.instance and self.instance.pk:
            self.fields['flight_number'].widget.attrs['readonly'] = True

    def clean_flight_number(self):
        """Валидация формата номера рейса: AAA-NNN"""
        flight_number = self.cleaned_data.get('flight_number')
        if not re.match(r'^[A-Z]{3}-\d{3}$', flight_number.upper()):
            raise forms.ValidationError('Номер рейса должен быть в формате AAA-NNN (например, SVO-123)')
        return flight_number.upper()

    def clean_free_seats(self):
        """Проверка: свободных мест не больше общего количества"""
        free_seats = self.cleaned_data.get('free_seats')
        total_seats = self.cleaned_data.get('total_seats')

        if total_seats and free_seats and free_seats > total_seats:
            raise forms.ValidationError('Свободных мест не может быть больше общего количества')
        return free_seats

    def clean(self):
        """Проверка: аэропорт отправления ≠ аэропорт прибытия"""
        cleaned_data = super().clean()
        departure = cleaned_data.get('departure_airport')
        arrival = cleaned_data.get('arrival_airport')

        if departure and arrival and departure == arrival:
            raise forms.ValidationError('Аэропорт отправления и прибытия не могут совпадать')
        return cleaned_data

class FlightSearchForm(forms.Form):
    """Форма поиска рейсов"""
    SEARCH_CHOICES = [
        ('number', 'По номеру рейса'),
        ('arrival', 'По аэропорту прибытия'),
    ]
    search_type = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Тип поиска"
    )
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите запрос...'}),
        label="Запрос",
        required=False
    )

    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()
        search_type = self.cleaned_data.get('search_type')

        if search_type == 'number' and query:
            query = query.upper()
            if not re.match(r'^[A-Z]{3}-\d{3}$', query):
                raise forms.ValidationError('Номер рейса должен быть в формате AAA-NNN')
        return query