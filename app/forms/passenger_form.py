from django import forms
from app.models import Passenger
import re


class PassengerForm(forms.Form):
    """Форма регистрации пассажира (для API)"""
    passport_number = forms.CharField(
        max_length=11,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234-567890'}),
        label="Номер паспорта"
    )
    passport_issued_by = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'ОВД г. Москвы'}),
        label="Кем выдан"
    )
    passport_issue_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Дата выдачи"
    )
    full_name = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
        label="ФИО"
    )
    birth_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Дата рождения"
    )

    def clean_passport_number(self):
        passport = self.cleaned_data.get('passport_number')
        if not re.match(r'^\d{4}-\d{6}$', passport):
            raise forms.ValidationError('Формат: NNNN-NNNNNN')
        return passport


class PassengerSearchForm(forms.Form):
    """Форма поиска пассажиров"""
    SEARCH_CHOICES = [
        ('passport', 'По номеру паспорта'),
        ('name', 'По ФИО'),
    ]

    search_type = forms.ChoiceField(
        choices=SEARCH_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Тип поиска"
    )
    query = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите паспорт или ФИО...'
        }),
        label="Запрос"
    )

    def clean_query(self):
        query = self.cleaned_data.get('query', '').strip()
        search_type = self.cleaned_data.get('search_type')

        if search_type == 'passport' and query:
            if not re.match(r'^\d{4}-\d{6}$', query):
                raise forms.ValidationError(
                    'Номер паспорта должен быть в формате NNNN-NNNNNN'
                )
        return query