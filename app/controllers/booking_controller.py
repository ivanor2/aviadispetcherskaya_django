# app/controllers/booking_controller.py
import requests
from django.conf import settings
from app.utils import parse_v2_validation_errors, normalize_api_response
from .flight_controller import FlightController


class BookingController:
    BASE_URL = f"{settings.API_BASE_URL}/bookings"

    @staticmethod
    def get_all_bookings(page: int = 1, size: int = 20, access_token: str = None, **filters) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        params = {'page': page, 'size': size}
        params.update({k: v for k, v in filters.items() if v is not None})

        try:
            response = requests.get(BookingController.BASE_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            return normalize_api_response(response.json(), page)
        except requests.RequestException:
            return {'items': [], 'total': 0, 'page': page, 'pages': 1}

    @staticmethod
    def create_booking(payload: dict, access_token: str = None) -> tuple[bool, list | None, str]:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        } if access_token else {'Content-Type': 'application/json'}

        try:
            response = requests.post(f"{BookingController.BASE_URL}/", json=payload, headers=headers, timeout=10)

            if response.status_code == 201:
                data = response.json()
                bookings = data if isinstance(data, list) else [data]
                booking_code = bookings[0].get('bookingCode') or bookings[0].get('booking_code',
                                                                                 'N/A') if bookings else 'N/A'
                return True, bookings, f'Билеты оформлены! Код: {booking_code}'

            if response.status_code == 422:
                return False, None, parse_v2_validation_errors(response)

            detail = response.json().get('detail', 'Ошибка оформления')
            return False, response.json(), detail

        except requests.RequestException as e:
            return False, None, f'Сбой API: {e}'

    @staticmethod
    def add_connections(booking_code: str, flight_ids: list, access_token: str = None) -> tuple[bool, list | None, str]:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        } if access_token else {'Content-Type': 'application/json'}

        try:
            response = requests.post(
                f"{BookingController.BASE_URL}/{booking_code}/connections",
                json={'flightIds': flight_ids},
                headers=headers,
                timeout=10
            )

            if response.status_code == 201:
                data = response.json()
                bookings = data if isinstance(data, list) else [data]
                return True, bookings, 'Билеты на пересадку успешно добавлены'

            if response.status_code == 422:
                return False, None, parse_v2_validation_errors(response)

            detail = response.json().get('detail', 'Ошибка добавления пересадки')
            return False, None, detail

        except requests.RequestException as e:
            return False, None, f'Сбой API: {e}'

    @staticmethod
    def cancel_booking(booking_id: int, access_token: str = None) -> bool:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.delete(f"{BookingController.BASE_URL}/{booking_id}", headers=headers, timeout=10)
            return response.status_code == 204
        except requests.RequestException:
            return False

    @staticmethod
    def get_bookings_by_flight(flight_id: int, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{BookingController.BASE_URL}/by-flight/{flight_id}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else data.get('items', [])
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def get_bookings_by_passport(passport: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{BookingController.BASE_URL}/by-passenger/{passport}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def get_bookings_by_passport_enriched(passport: str, access_token: str = None) -> list:
        """Получает бронирования пассажира с подстановкой номеров рейсов"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{BookingController.BASE_URL}/by-passenger/{passport}",
                headers=headers,
                timeout=5
            )
            if response.status_code != 200:
                return []

            bookings = response.json()
            if not isinstance(bookings, list):
                bookings = bookings.get('items', []) if isinstance(bookings, dict) else [bookings] if isinstance(
                    bookings, dict) else []

            enriched = []
            for b in bookings:
                flight_id = b.get('flightId') or b.get('flight_id')
                flight_info = FlightController.get_flight_short_info(flight_id, access_token) if flight_id else None

                enriched.append({
                    **b,
                    'flight_number': flight_info.get('flight_number') if flight_info else None,
                    'departure_icao': flight_info.get('departure_airport_icao') if flight_info else None,
                    'arrival_icao': flight_info.get('arrival_airport_icao') if flight_info else None,
                })
            return enriched
        except requests.RequestException:
            return []