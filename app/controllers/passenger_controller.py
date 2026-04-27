import requests
from django.conf import settings

class PassengerController:
    BASE_URL = f"{settings.API_BASE_URL}/passengers"

    @staticmethod
    def get_all_passengers(page: int = 1, size: int = 50, access_token: str = None) -> dict:
        """Получение списка пассажиров для выпадающего списка"""
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                PassengerController.BASE_URL,
                params={'page': page, 'size': size},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {'items': [], 'total': 0}

    @staticmethod
    def search_by_passport(passport: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{PassengerController.BASE_URL}/search/by-passport/{passport}", headers=headers, timeout=5)
            if response.status_code == 404: return []
            response.raise_for_status()
            return [response.json()]
        except requests.RequestException:
            return []

    @staticmethod
    def search_by_name(name: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(f"{PassengerController.BASE_URL}/search/by-name/{name}", headers=headers, timeout=5)
            if response.status_code == 404: return []
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []

    @staticmethod
    def create_passenger(payload: dict, access_token: str = None) -> tuple[bool, dict | None, str]:
        """
        Создание нового пассажира через API.
        Returns: (success, data_or_error, message)
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        } if access_token else {'Content-Type': 'application/json'}

        try:
            response = requests.post(
                PassengerController.BASE_URL,
                json=payload,
                headers=headers,
                timeout=10
            )
            if response.status_code in (200, 201):
                return True, response.json(), 'Пассажир успешно зарегистрирован'

            # Обработка ошибок валидации
            detail = response.json().get('detail', 'Ошибка при создании пассажира')
            return False, response.json(), detail

        except requests.RequestException as e:
            return False, None, f'Ошибка подключения к API: {e}'