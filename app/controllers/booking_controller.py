import requests
from django.conf import settings

class BookingController:
    BASE_URL = f"{settings.API_BASE_URL}/bookings"

    @staticmethod
    def create_booking(payload: dict, access_token: str = None) -> tuple[bool, dict | None, str]:
        """payload: {'flightId': int, 'passengerId': int}"""
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'} if access_token else {}
        try:
            response = requests.post(BookingController.BASE_URL, json=payload, headers=headers, timeout=10)
            if response.status_code == 201:
                data = response.json()
                return True, data, f'Билет оформлен! Код: {data.get("bookingCode")}'
            detail = response.json().get('detail', 'Ошибка оформления')
            return False, response.json(), detail
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