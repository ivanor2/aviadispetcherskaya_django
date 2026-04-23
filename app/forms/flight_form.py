import re
import requests
from django import forms
from django.conf import settings

class FlightForm(forms.Form):
    airline = forms.ChoiceField(
        label="Авиакомпания",
        widget=forms.Select(attrs={'class': 'form-select'}),
        choices=[('', '---------')]
    )
    flight_number = forms.CharField(
        max_length=3,
        label="Номер рейса (цифры)",
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'pattern': '\\d{3}',
            'title': 'Введите ровно 3 цифры',
            'inputmode': 'numeric'
        })
    )
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
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}

        # ✅ Загрузка авиакомпаний из API
        try:
            resp = requests.get(f"{settings.API_BASE_URL}/airlines", headers=headers, timeout=5)
            if resp.status_code == 200:
                airlines = resp.json()
                self.fields['airline'].choices = [('', '---------')] + \
                    [(a['code'], f"{a['code']} — {a['name']}") for a in airlines]
        except Exception:
            pass

        # ✅ Загрузка аэропортов
        try:
            resp = requests.get(f"{settings.API_BASE_URL}/airports", params={'page': 1, 'size': 100}, headers=headers, timeout=5)
            if resp.status_code == 200:
                airports = resp.json().get('items', [])
                choices = [('', '---------')] + [(str(a['icao_code']), f"{a['icao_code']} — {a['name']}") for a in airports]
                self.fields['departure_airport'].choices = choices
                self.fields['arrival_airport'].choices = choices
        except Exception:
            pass

    def clean_flight_number(self):
        fn = self.cleaned_data.get('flight_number', '').strip()
        if not re.match(r'^\d{3}$', fn):
            raise forms.ValidationError('Номер рейса должен состоять ровно из 3 цифр')
        return fn

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