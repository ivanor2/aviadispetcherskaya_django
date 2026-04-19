from django import forms
from app.models import Passenger
import re


class PassengerForm(forms.ModelForm):
    """Форма регистрации пассажира"""

    class Meta:
        model = Passenger
        fields = [
            'passport_number', 'passport_issued_by',
            'passport_issue_date', 'full_name', 'birth_date'
        ]
        widgets = {
            'passport_issue_date': forms.DateInput(attrs={'type': 'date'}),
            'birth_date': forms.DateInput(attrs={'type': 'date'}),
        }

    def clean_passport_number(self):
        """Валидация формата паспорта: NNNN-NNNNNN"""
        passport = self.cleaned_data.get('passport_number')
        if not re.match(r'^\d{4}-\d{6}$', passport):
            raise forms.ValidationError(
                'Номер паспорта должен быть в формате NNNN-NNNNNN'
            )
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