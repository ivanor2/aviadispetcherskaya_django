import requests
from django.conf import settings

class FlightController:
    BASE_URL = f"{settings.API_BASE_URL}/flights"

    @staticmethod
    def get_all_flights(page: int = 1, size: int = 20, access_token: str = None) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                FlightController.BASE_URL,
                params={'page': page, 'size': size},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return {'items': [], 'total': 0, 'page': page, 'pages': 0}

    @staticmethod
    def search_by_number(flight_number: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{FlightController.BASE_URL}/by-number/{flight_number}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 404: return []
            response.raise_for_status()
            return [response.json()]
        except requests.RequestException:
            return []

    @staticmethod
    def search_by_arrival(query: str, access_token: str = None) -> list:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{FlightController.BASE_URL}/search/by-arrival/{query}",
                headers=headers,
                timeout=10
            )
            if response.status_code == 404: return []
            response.raise_for_status()
            return response.json()
        except requests.RequestException:
            return []