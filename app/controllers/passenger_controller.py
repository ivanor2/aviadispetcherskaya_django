import requests
from django.conf import settings

class PassengerController:
    BASE_URL = f"{settings.API_BASE_URL}/passengers"

    @staticmethod
    def get_all_passengers(page: int = 1, size: int = 20, access_token: str = None) -> dict:
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
            return {'items': [], 'total': 0, 'page': page, 'pages': 0}

    @staticmethod
    def search_by_passport(passport: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{PassengerController.BASE_URL}/search/by-passport/{passport}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 404: return []
            response.raise_for_status()
            return [response.json()]
        except requests.RequestException:
            return []

    @staticmethod
    def search_by_name(name: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{PassengerController.BASE_URL}/search/by-name/{name}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 404: return []
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []