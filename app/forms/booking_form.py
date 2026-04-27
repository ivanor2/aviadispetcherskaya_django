from django import forms
from app.models import Booking, Flight, Passenger


class BookingForm(forms.Form):
    """Форма продажи билета"""

    # Выбор существующего пассажира
    passenger = forms.ChoiceField(
        label="Выберите пассажира",
        choices=[('', '--- Выберите или создайте нового ---')],
        widget=forms.Select(attrs={'class': 'form-select', 'id': 'id_passenger_select'}),
        required=False
    )

    # Переключатель режима
    is_new_passenger = forms.BooleanField(
        required=False,
        label="Зарегистрировать нового пассажира",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input', 'id': 'id_is_new_passenger'})
    )

    # Поля для нового пассажира
    new_passport_number = forms.CharField(
        max_length=11, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '1234-567890'})
    )
    new_full_name = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'})
    )
    new_passport_issued_by = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'УФМС России...'})
    )
    new_passport_issue_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    new_birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )

    def __init__(self, *args, access_token=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Загружаем список пассажиров из API для выпадающего списка
        from app.controllers import PassengerController
        if access_token:
            data = PassengerController.get_all_passengers(page=1, size=100, access_token=access_token)
            items = data.get('items', [])
            # Формируем список (id, "ФИО (Паспорт)")
            choices = [('', '--- Выберите пассажира ---')] + [
                (str(p['id']),
                 f"{p.get('fullName', p.get('full_name'))} ({p.get('passportNumber', p.get('passport_number'))})")
                for p in items
            ]
            self.fields['passenger'].choices = choices

    def clean_passport_number(self):
        p = self.cleaned_data.get('new_passport_number')
        if p and not re.match(r'^\d{4}-\d{6}$', p):
            raise forms.ValidationError('Формат паспорта: NNNN-NNNNNN')
        return p

    def clean(self):
        cleaned_data = super().clean()
        is_new = cleaned_data.get('is_new_passenger')
        passenger_id = cleaned_data.get('passenger')

        if is_new:
            # Если новый пассажир, проверяем заполнение полей
            required_fields = ['new_passport_number', 'new_full_name', 'new_passport_issued_by',
                               'new_passport_issue_date', 'new_birth_date']
            for field in required_fields:
                if not cleaned_data.get(field):
                    self.add_error(field, 'Это поле обязательно при регистрации нового пассажира')
        else:
            # Если существующий, должен быть выбран
            if not passenger_id:
                self.add_error('passenger', 'Выберите пассажира или отметьте "Зарегистрировать нового"')

        return cleaned_data

class BookingCancelForm(forms.Form):
    """Форма отмены бронирования"""
    booking_id = forms.IntegerField(widget=forms.HiddenInput())
    flight_id = forms.IntegerField(widget=forms.HiddenInput())

    confirm = forms.BooleanField(
        required=True,
        label="Подтверждаю возврат билета",
        error_messages={'required': 'Необходимо подтвердить возврат'}
    )