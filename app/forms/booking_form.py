from django import forms
from app.models import Booking, Flight, Passenger


class BookingForm(forms.ModelForm):
    """Форма продажи билета"""

    # Поля для быстрого добавления нового пассажира
    is_new_passenger = forms.BooleanField(
        required=False,
        label="Зарегистрировать нового пассажира",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # Поля для нового пассажира (скрытые по умолчанию)
    new_passport_number = forms.CharField(
        max_length=11, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    new_full_name = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Booking
        fields = ['flight', 'passenger']
        widgets = {
            'flight': forms.Select(attrs={'class': 'form-select'}),
            'passenger': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Показываем только рейсы со свободными местами
        if 'flight' in self.fields:
            self.fields['flight'].queryset = Flight.objects.filter(
                free_seats__gt=0
            ).select_related('departure_airport', 'arrival_airport')

    def clean(self):
        cleaned_data = super().clean()
        flight = cleaned_data.get('flight')

        if flight and not flight.has_free_seats():
            raise forms.ValidationError(
                'На выбранный рейс нет свободных мест'
            )
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