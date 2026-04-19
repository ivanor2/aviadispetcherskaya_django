import requests
from django import forms
from django.conf import settings
import re

class FlightForm(forms.Form):
    """Форма создания/редактирования рейса (данные отправляются в FastAPI)"""
    flight_number = forms.CharField(
        max_length=10,
        label="№ авиарейса",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'SU-123'})
    )
    airline_name = forms.CharField(
        max_length=255,
        label="Авиакомпания",
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    # Используем ChoiceField, так как данные берем из API
    departure_airport = forms.ChoiceField(
        label="Аэропорт отправления",
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=[('', '---------')]
    )
    arrival_airport = forms.ChoiceField(
        label="Аэропорт прибытия",
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=[('', '---------')]
    )
    departure_date = forms.DateField(
        label="Дата отправления",
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    departure_time = forms.TimeField(
        label="Время отправления",
        widget=forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'})
    )
    total_seats = forms.IntegerField(
        label="Всего мест",
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )
    free_seats = forms.IntegerField(
        label="Свободных мест",
        min_value=0,
        required=False,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    def __init__(self, *args, access_token=None, **kwargs):
        super().__init__(*args, **kwargs)

        headers = {}
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'

        try:
            # ✅ Передаём headers в запрос
            resp = requests.get(
                f"{settings.API_BASE_URL}/airports",
                params={'page': 1, 'size': 100},
                headers=headers,
                timeout=5
            )
            if resp.status_code == 200:
                airports = resp.json().get('items', [])
                choices = [('', '---------')] + [
                    (str(a['icao_code']), f"{a['icao_code']} — {a['name']}") for a in airports
                ]
                self.fields['departure_airport'].choices = choices
                self.fields['arrival_airport'].choices = choices
        except Exception:
            pass


    def clean_flight_number(self):
        flight_number = self.cleaned_data.get('flight_number', '').upper()
        # Разрешаем 2 или 3 буквы (как в схеме API)
        if not re.match(r'^[A-Z]{2,3}-\d{3}$', flight_number):
            raise forms.ValidationError('Формат: AA-NNN или AAA-NNN')
        return flight_number

    def clean_free_seats(self):
        free_seats = self.cleaned_data.get('free_seats')
        total_seats = self.cleaned_data.get('total_seats')
        if total_seats and free_seats is not None and free_seats > total_seats:
            raise forms.ValidationError('Свободных мест не может быть больше общего количества')
        return free_seats if free_seats is not None else total_seats

    def clean(self):
        cleaned_data = super().clean()
        dep = cleaned_data.get('departure_airport')
        arr = cleaned_data.get('arrival_airport')
        if dep and arr and dep == arr:
            raise forms.ValidationError('Аэропорты отправления и прибытия не могут совпадать')
        return cleaned_data


class FlightSearchForm(forms.Form):
    """Форма поиска рейсов"""
    SEARCH_CHOICES = [
        ('number', 'По номеру рейса'),
        ('arrival', 'По аэропорту прибытия'),
        ('date', 'По дате'),
    ]
    search_type = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Тип поиска"
    )
    query = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите запрос...'
        }),
        label="Запрос",
        required=False
    )


    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()
        search_type = self.cleaned_data.get('search_type')

        if search_type == 'number' and query:
            query = query.upper()
            # ✅ Теперь принимает 2 или 3 буквы (как в FastAPI)
            if not re.match(r'^[A-Z]{2,3}-\d{3}$', query):
                raise forms.ValidationError('Формат: AA-NNN или AAA-NNN (например, SU-123)')
        return query