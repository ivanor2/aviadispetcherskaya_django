import requests
from django.conf import settings

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