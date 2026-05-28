import re
from django import forms
from app.controllers import PassengerController, FlightController
import logging

logger = logging.getLogger(__name__)


class BookingForm(forms.Form):
    connection_flight_id = forms.ChoiceField(
        required=False,
        choices=[('', '--- Не нужна пересадка ---')],
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Рейс для пересадки (опционально)"
    )

    baggage_allowed = forms.BooleanField(
        label="Добавить багаж (фиксированный сбор)",
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    custom_additional_fee = forms.FloatField(
        label="Дополнительные сборы (руб.)",
        required=False,
        min_value=0.0,
        initial=0.0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'placeholder': '0.00'}),
        help_text="Опционально: штрафы, спец. услуги и т.д."
    )

    payment_type = forms.ChoiceField(
        choices=[('card', 'Карта'), ('cash', 'Наличные'), ('online', 'Онлайн')],
        label="Способ оплаты",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class_type = forms.ChoiceField(
        choices=[('economy', 'Эконом'), ('business', 'Бизнес (+100% к стоимости)'),
                 ('first', 'Первый класс (+200% к стоимости)')],
        label="Класс обслуживания",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, access_token=None, current_flight_id=None, **kwargs):
        self.access_token = access_token
        self.current_flight_id = current_flight_id
        super().__init__(*args, **kwargs)

        self.passenger_choices = [('', '-- Выберите пассажира --')]
        self.seat_choices = [('', '-- Автовыбор места --')]

        if access_token:
            try:
                # Загрузка пассажиров
                p_items = []
                p_page = 1
                while True:
                    p_data = PassengerController.get_all_passengers(page=p_page, size=100, access_token=access_token)
                    p_items.extend(p_data.get('items', []))
                    if p_page >= p_data.get('pages', 1): break
                    p_page += 1

                for p in p_items:
                    p_id = str(p.get('id'))
                    name = p.get('fullName') or p.get('full_name') or 'Без имени'
                    passport = p.get('passportNumber') or p.get('passport_number') or '?'
                    self.passenger_choices.append((p_id, f"{name} ({passport})"))

                # Загрузка рейсов для пересадки
                f_items = []
                f_page = 1
                while True:
                    f_data = FlightController.get_all_flights(page=f_page, size=100, access_token=access_token)
                    f_items.extend(f_data.get('items', []))
                    if f_page >= f_data.get('pages', 1): break
                    f_page += 1

                flight_choices = [('', '--- Не нужна пересадка ---')]
                for f in f_items:
                    fid = str(f.get('id'))
                    if current_flight_id and int(fid) == int(current_flight_id): continue

                    free_seats = f.get('free_seats') or f.get('freeSeats', 0)
                    if not free_seats or free_seats <= 0: continue

                    fnum = f.get('flightNumber') or f.get('flight_number', 'N/A')
                    dep = f.get('departureAirportIcao') or f.get('departure_airport_icao', '?')
                    arr = f.get('arrivalAirportIcao') or f.get('arrival_airport_icao', '?')
                    date = f.get('departureDate') or f.get('departure_date', '?')

                    label = f"Рейс {fnum} | {dep} → {arr} | {date} (мест: {free_seats})"
                    flight_choices.append((fid, label))

                self.fields['connection_flight_id'].choices = flight_choices

                if current_flight_id:
                    current_flight = FlightController.get_flight_by_id(current_flight_id, access_token)
                    if current_flight:
                        # Вариант А: Если FastAPI уже возвращает массив свободных мест
                        api_seats = current_flight.get('availableSeats') or current_flight.get('available_seats')

                        if api_seats and isinstance(api_seats, list):
                            for seat in api_seats:
                                self.seat_choices.append((seat, f"Место {seat}"))

                        # Вариант Б: Генерируем стандартную рассадку (A, B, C, D, E, F)
                        else:
                            total_seats = current_flight.get('totalSeats') or current_flight.get('total_seats') or 150
                            seats_generated = 0

                            # По 6 мест в ряду
                            for row in range(1, (total_seats // 6) + 2):
                                for letter in ['A', 'B', 'C', 'D', 'E', 'F']:
                                    if seats_generated < total_seats:
                                        seat_name = f"{row}{letter}"
                                        self.seat_choices.append((seat_name, f"Место {seat_name}"))
                                        seats_generated += 1

            except Exception as e:
                logger.error(f"BookingForm: Ошибка загрузки данных: {e}")
                self.passenger_choices.append(('', 'Ошибка подключения к API'))

    def clean(self):
        cleaned_data = super().clean()

        if self.current_flight_id and self.access_token:
            flight = FlightController.get_flight_by_id(self.current_flight_id, self.access_token)

            if flight:
                raw_base_price = flight.get('basePrice') or flight.get('base_price') or 0.0
                baggage_price = flight.get('baggagePrice') or flight.get('baggage_price') or 0.0

                # === РАСЧЕТ СТОИМОСТИ НА ОСНОВЕ КЛАССА ===
                class_type = cleaned_data.get('class_type', 'economy')
                if class_type == 'business':
                    final_base_price = raw_base_price * 2.0  # Бизнес в 2 раза дороже
                elif class_type == 'first':
                    final_base_price = raw_base_price * 3.0  # Первый класс в 3 раза дороже
                else:
                    final_base_price = raw_base_price  # Эконом без изменений

                cleaned_data['base_price'] = final_base_price
                cleaned_data['tax'] = final_base_price * 0.22  # НДС 22% от новой базовой цены

                # Итоговые дополнительные сборы = Сбор за багаж + Ручной сбор
                custom_fee = cleaned_data.get('custom_additional_fee') or 0.0
                if cleaned_data.get('baggage_allowed'):
                    cleaned_data['additional_fees'] = baggage_price + custom_fee
                else:
                    cleaned_data['additional_fees'] = custom_fee

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