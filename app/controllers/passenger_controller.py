# app/controllers/passenger_controller.py
import requests
from django.conf import settings
from app.utils import parse_v2_validation_errors, normalize_api_response
import logging
logger = logging.getLogger(__name__)

class PassengerController:
    BASE_URL = f"{settings.API_BASE_URL}/passengers"

    @staticmethod
    def get_all_passengers(page: int = 1, size: int = 50, access_token: str = None) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        params = {'page': page, 'size': size}
        try:
            response = requests.get(PassengerController.BASE_URL, params=params, headers=headers, timeout=10)
            logger.info(f"📡 API v2 GET /passengers -> Status: {response.status_code}")
            response.raise_for_status()
            return normalize_api_response(response.json(), page)
        except requests.RequestException:
            return {'items': [], 'total': 0, 'page': page, 'pages': 1}

    @staticmethod
    def search_by_passport(passport: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{PassengerController.BASE_URL}/search/by-passport/{passport}", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return [data] if isinstance(data, dict) else data
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def search_by_name(name: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{PassengerController.BASE_URL}/search/by-name/{name}", headers=headers, timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data if isinstance(data, list) else [data] if isinstance(data, dict) else []
            return []
        except requests.RequestException:
            return []

    @staticmethod
    def create_passenger(payload: dict, access_token: str = None) -> tuple[bool, dict | None, str]:
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        try:
            response = requests.post(PassengerController.BASE_URL, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                return True, response.json(), 'Пассажир зарегистрирован'
            return False, response.json(), f'Ошибка: {response.status_code}'
        except requests.RequestException as e:
            return False, None, str(e)

    @staticmethod
    def get_passenger_by_id(passenger_id: int, access_token: str = None) -> dict | None:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{PassengerController.BASE_URL}/{passenger_id}", headers=headers, timeout=5)
            return response.json() if response.status_code == 200 else None
        except requests.RequestException:
            return None

    @staticmethod
    def delete_passenger(passenger_id: int, access_token: str = None) -> tuple[bool, str]:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.delete(f"{PassengerController.BASE_URL}/{passenger_id}", headers=headers, timeout=10)
            if response.status_code == 204:
                return True, 'Удалено'
            return False, response.json().get('detail', 'Ошибка')
        except requests.RequestException:
            return False, 'Сбой подключения'

