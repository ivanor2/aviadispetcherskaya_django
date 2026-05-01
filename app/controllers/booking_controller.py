import requests
from django.conf import settings

from app.controllers.passenger_controller import PassengerController
from app.controllers.flight_controller import FlightController


class BookingController:
    BASE_URL = f"{settings.API_BASE_URL}/bookings/"

    @staticmethod
    def create_booking(payload: dict, access_token: str = None) -> tuple[bool, list | None, str]:
        headers = {'Authorization': f'Bearer {access_token}',
                   'Content-Type': 'application/json'} if access_token else {}
        try:
            response = requests.post(BookingController.BASE_URL, json=payload, headers=headers, timeout=10)
            if response.status_code == 201:
                data = response.json()
                booking_code = data[0].get("bookingCode", "N/A") if data else "N/A"
                return True, data, f'Билеты оформлены! Код: {booking_code}'
            detail = response.json().get('detail', 'Ошибка оформления')
            return False, response.json(), detail
        except requests.RequestException as e:
            return False, None, f'Сбой API: {e}'

    @staticmethod
    def add_connections(booking_code: str, flight_ids: list, access_token: str = None) -> tuple[bool, list | None, str]:
        headers = {'Authorization': f'Bearer {access_token}',
                   'Content-Type': 'application/json'} if access_token else {}
        try:
            response = requests.post(
                f"{BookingController.BASE_URL}/{booking_code}/connections",
                json={"flightIds": flight_ids},
                headers=headers, timeout=10
            )
            if response.status_code == 201:
                return True, response.json(), 'Билеты на пересадку успешно добавлены'
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
            response = requests.get(f"{BookingController.BASE_URL}/by-flight/{flight_id}", headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def get_bookings_by_passport(passport: str, access_token: str = None) -> list:
        """Получение всех бронирований пассажира по номеру паспорта"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            # ✅ API ожидает именно этот эндпоинт
            response = requests.get(
                f"{BookingController.BASE_URL}by-passenger/{passport}",
                headers=headers, timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def delete_passenger(passenger_id: int, access_token: str = None) -> tuple[bool, str]:
        """Удаление пассажира по ID"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.delete(
                f"{PassengerController.BASE_URL}/{passenger_id}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 204:
                return True, 'Пассажир успешно удалён'
            detail = response.json().get('detail', 'Ошибка при удалении')
            return False, detail
        except requests.RequestException as e:
            return False, f'Ошибка подключения к API: {e}'

    @staticmethod
    def get_bookings_by_passport_enriched(passport: str, access_token: str = None) -> list:
        """Получает бронирования пассажира с подстановкой номеров рейсов"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            # 1. Получаем базовые бронирования
            response = requests.get(
                f"{BookingController.BASE_URL}/by-passenger/{passport}",
                headers=headers,
                timeout=5
            )
            if response.status_code != 200:
                return []

            bookings = response.json()

            # 2. Для каждого бронирования подгружаем номер рейса
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