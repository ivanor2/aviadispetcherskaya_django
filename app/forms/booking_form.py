import re
from django import forms
from app.controllers import PassengerController, FlightController
import logging

logger = logging.getLogger(__name__)


class BookingForm(forms.Form):
    # Загружаем рейсы для выбора пересадки
    connection_flight_id = forms.ChoiceField(
        required=False,
        choices=[('', '--- Не нужна пересадка ---')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Рейс для пересадки (опционально)"
    )

    def __init__(self, *args, access_token=None, current_flight_id=None, **kwargs):
        super().__init__(*args, **kwargs)

        # 1. Загружаем пассажиров
        self.passenger_choices = [('', '-- Выберите пассажира --')]

        if access_token:
            try:
                # Пассажиры
                p_data = PassengerController.get_all_passengers(page=1, size=100, access_token=access_token)
                p_items = p_data.get('items', [])
                for p in p_items:
                    p_id = str(p.get('id'))
                    name = p.get('fullName') or p.get('full_name') or 'Без имени'
                    passport = p.get('passportNumber') or p.get('passport_number') or '?'
                    self.passenger_choices.append((p_id, f"{name} ({passport})"))

                # 2. Загружаем рейсы для пересадки
                f_data = FlightController.get_all_flights(page=1, size=100, access_token=access_token)
                f_items = f_data.get('items', [])

                flight_choices = [('', '--- Не нужна пересадка ---')]
                for f in f_items:
                    fid = str(f.get('id'))
                    fid_int = int(fid)

                    # Исключаем текущий рейс из списка пересадок
                    if current_flight_id and fid_int == int(current_flight_id):
                        continue

                    # Показываем только рейсы с доступными местами
                    free_seats = f.get('free_seats') or f.get('freeSeats', 0)
                    if not free_seats or free_seats <= 0:
                        continue

                    # Формируем красивую метку
                    fnum = f.get('flightNumber') or f.get('flight_number', 'N/A')
                    dep = f.get('departureAirportIcao') or f.get('departure_airport_icao', '?')
                    arr = f.get('arrivalAirportIcao') or f.get('arrival_airport_icao', '?')
                    date = f.get('departureDate') or f.get('departure_date', '?')

                    label = f"✈️ {fnum} | {dep} → {arr} | {date} (мест: {free_seats})"
                    flight_choices.append((fid, label))

                self.fields['connection_flight_id'].choices = flight_choices

            except Exception as e:
                logger.error(f"BookingForm: Ошибка загрузки данных: {e}")
                self.passenger_choices.append(('', '⚠️ Ошибка подключения к API'))

    def clean(self):
        cleaned_data = super().clean()
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