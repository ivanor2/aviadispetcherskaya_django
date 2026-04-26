import requests
from django.conf import settings

class FlightController:
    BASE_URL = f"{settings.API_BASE_URL}/flights"

    @staticmethod
    def get_all_flights(page: int = 1, size: int = 20, access_token: str = None) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(FlightController.BASE_URL, params={'page': page, 'size': size}, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
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
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'} if access_token else {}
        try:
            response = requests.post(FlightController.BASE_URL, json=payload, headers=headers, timeout=10)
            if response.status_code in (200, 201):
                return True, response.json(), 'Рейс успешно создан'
            detail = response.json().get('detail', 'Ошибка создания')
            return False, response.json(), detail
        except requests.RequestException as e:
            return False, None, f'Ошибка подключения: {e}'

    @staticmethod
    def get_flight_with_passengers(flight_number: str, access_token: str = None) -> dict:
        """Возвращает {'flight': {...}, 'passengers': [...]"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{FlightController.BASE_URL}/by-number/{flight_number}", headers=headers, timeout=5)
            if response.status_code == 200:
                return response.json()
            return {'flight': None, 'passengers': []}
        except requests.RequestException:
            return {'flight': None, 'passengers': []}

    @staticmethod
    def search_by_arrival(query: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{FlightController.BASE_URL}/search/by-arrival/{query}", headers=headers, timeout=5)
            if response.status_code == 404: return []
            response.raise_for_status()
            return response.json()
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
        """Удаляет все рейсы и связанные бронирования (требует роль admin)"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.delete(
                f"{FlightController.BASE_URL}/?confirm=true",
                headers=headers,
                timeout=15
            )
            if response.status_code == 204:
                return True, 'Все рейсы и бронирования успешно удалены'

            # Безопасное чтение ошибки
            try:
                detail = response.json().get('detail', 'Ошибка удаления')
            except ValueError:
                detail = f'Ошибка API: {response.status_code}'
            return False, detail
        except requests.RequestException as e:
            return False, f'Сбой подключения к API: {e}'