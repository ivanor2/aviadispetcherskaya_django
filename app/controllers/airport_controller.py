import requests
from django.conf import settings
from app.utils import parse_v2_validation_errors, normalize_api_response

class AirportController:
    BASE_URL = f"{settings.API_BASE_URL}/airports"

    @staticmethod
    def get_all(page=1, size=20, access_token=None):
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            resp = requests.get(AirportController.BASE_URL, params={'page': page, 'size': size}, headers=headers, timeout=10)
            resp.raise_for_status()
            return normalize_api_response(resp.json(), page)
        except requests.RequestException:
            return {'items': [], 'total': 0, 'page': page, 'pages': 1}

    @staticmethod
    def get_by_id(airport_id, access_token=None):
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            resp = requests.get(f"{AirportController.BASE_URL}/{airport_id}", headers=headers, timeout=5)
            return resp.json() if resp.status_code == 200 else None
        except: return None

    @staticmethod
    def create(data, access_token=None):
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        try:
            resp = requests.post(AirportController.BASE_URL, json=data, headers=headers, timeout=10)
            if resp.status_code in (200, 201): return True, resp.json(), 'Аэропорт успешно создан'
            return False, resp.json(), parse_v2_validation_errors(resp) if resp.status_code == 422 else f'Ошибка API: {resp.status_code}'
        except requests.RequestException as e: return False, None, str(e)

    @staticmethod
    def update(airport_id, data, access_token=None):
        headers = {'Authorization': f'Bearer {access_token}', 'Content-Type': 'application/json'}
        try:
            resp = requests.put(f"{AirportController.BASE_URL}/{airport_id}", json=data, headers=headers, timeout=10)
            if resp.status_code in (200, 204): return True, resp.json(), 'Данные аэропорта обновлены'
            return False, resp.json(), parse_v2_validation_errors(resp) if resp.status_code == 422 else f'Ошибка API: {resp.status_code}'
        except requests.RequestException as e: return False, None, str(e)

    @staticmethod
    def delete(airport_id, access_token=None):
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            resp = requests.delete(f"{AirportController.BASE_URL}/{airport_id}", headers=headers, timeout=10)
            return resp.status_code in (200, 204)
        except: return False