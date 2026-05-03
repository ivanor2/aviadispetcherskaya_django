# app/controllers/flight_controller.py
import requests
from django.conf import settings
from app.utils import parse_v2_validation_errors, normalize_api_response
import logging

logger = logging.getLogger(__name__)


class FlightController:
    BASE_URL = f"{settings.API_BASE_URL}/flights"

    @staticmethod
    def get_all_flights(page: int = 1, size: int = 20, access_token: str = None) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        params = {'page': page, 'size': size}

        try:
            response = requests.get(FlightController.BASE_URL, params=params, headers=headers, timeout=10)

            # 🔍 ЛОГИРОВАНИЕ ОТВЕТА (смотри в консоли Django!)
            logger.info(f"📡 API v2 GET /flights -> Status: {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"⚠️ API Error: {response.text[:200]}")

            response.raise_for_status()
            return normalize_api_response(response.json(), page)

        except requests.RequestException as e:
            logger.error(f"❌ FlightController Connection Error: {e}")
            return {'items': [], 'total': 0, 'page': page, 'pages': 0}

    @staticmethod
    def get_flight_by_id(flight_id: int, access_token: str = None) -> dict | None:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{FlightController.BASE_URL}/{flight_id}", headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException:
            return None

    @staticmethod
    def create_flight(payload: dict, access_token: str = None) -> tuple[bool, dict | None, str]:
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        try:
            response = requests.post(FlightController.BASE_URL, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                return True, response.json(), 'Рейс успешно создан'
            return False, response.json(), f'Ошибка API: {response.status_code}'
        except requests.RequestException as e:
            return False, None, str(e)

    @staticmethod
    def get_flight_with_passengers(flight_number: str, access_token: str = None) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{FlightController.BASE_URL}/by-number/{flight_number}", headers=headers,
                                    timeout=5)
            if response.status_code == 200:
                return response.json()
            return {'flight': None, 'passengers': []}
        except requests.RequestException:
            return {'flight': None, 'passengers': []}

    @staticmethod
    def search_by_arrival(query: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{FlightController.BASE_URL}/search/by-arrival/{query}", headers=headers,
                                    timeout=5)
            if response.status_code in (200, 404):
                data = response.json()
                return data if isinstance(data, list) else data.get('items', [])
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def delete_flight(flight_id: int, access_token: str = None) -> bool:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.delete(f"{FlightController.BASE_URL}/{flight_id}", headers=headers, timeout=10)
            return response.status_code == 204
        except requests.RequestException:
            return False

    @staticmethod
    def delete_all_flights(access_token: str = None) -> tuple[bool, str]:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.delete(f"{FlightController.BASE_URL}/?confirm=true", headers=headers, timeout=15)
            if response.status_code == 204:
                return True, 'Все рейсы удалены'
            return False, response.json().get('detail', 'Ошибка удаления')
        except requests.RequestException:
            return False, 'Сбой подключения'

    @staticmethod
    def get_flight_short_info(flight_id: int, access_token: str = None) -> dict | None:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{FlightController.BASE_URL}/{flight_id}", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': data.get('id'),
                    'flight_number': data.get('flightNumber') or data.get('flight_number'),
                    'departure_airport_icao': data.get('departureAirportIcao') or data.get('departure_airport_icao'),
                    'arrival_airport_icao': data.get('arrivalAirportIcao') or data.get('arrival_airport_icao'),
                }
            return None
        except requests.RequestException:
            return None

