import requests
from django.conf import settings
from app.forms import BookingForm


class BookingController:
    """Контроллер для работы с бронированиями через API"""

    BASE_URL = f"{settings.API_BASE_URL}/bookings"

    @staticmethod
    def create_booking(form: BookingForm) -> tuple[bool, dict | None, str]:
        """
        Продать билет (создать бронирование) через форму
        Returns: (success, data_or_errors, message)
        """
        if not form.is_valid():
            return False, form.errors, 'Ошибка валидации формы'

        try:
            response = requests.post(
                BookingController.BASE_URL,
                json=form.cleaned_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            return True, response.json(), f'Билет оформлен! Код: {response.json().get("booking_code")}'
        except requests.RequestException as e:
            return False, None, f'Ошибка API: {e}'

    @staticmethod
    def cancel_booking(booking_id: int) -> bool:
        """Отменить продажу билета (возврат)"""
        try:
            response = requests.delete(
                f"{BookingController.BASE_URL}/{booking_id}",
                timeout=10
            )
            return response.status_code == 204
        except requests.RequestException:
            return False

    @staticmethod
    def get_bookings_by_flight(flight_id: int) -> list:
        """Получить все бронирования для рейса"""
        try:
            response = requests.get(
                f"{BookingController.BASE_URL}/flight/{flight_id}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('items', [])
        except requests.RequestException:
            return []

    @staticmethod
    def get_bookings_by_passenger(passenger_id: int) -> list:
        """Получить все бронирования пассажира"""
        try:
            response = requests.get(
                f"{BookingController.BASE_URL}/passenger/{passenger_id}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            return data.get('items', [])
        except requests.RequestException:
            return []