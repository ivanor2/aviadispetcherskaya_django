# app/controllers/auth_controller.py
import requests
from django.conf import settings
import json
from app.utils import parse_v2_validation_errors, normalize_api_response


class AuthController:
    BASE_URL = f"{settings.API_BASE_URL}/auth"

    @staticmethod
    def login(username: str, password: str) -> tuple[bool, dict | None, str]:
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/login",
                json={'username': username, 'password': password},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 401:
                return False, None, 'Неверный логин или пароль'

            if response.status_code == 422:
                return False, None, parse_v2_validation_errors(response)

            response.raise_for_status()

            if not response.text.strip():
                return False, None, 'Пустой ответ от API'

            data = response.json()
            return True, data, 'Вход выполнен успешно'

        except json.JSONDecodeError as e:
            return False, None, f'Невалидный ответ от API: {response.text[:100]}'
        except requests.RequestException as e:
            return False, None, f'Ошибка подключения к API: {e}'

    @staticmethod
    def register(username: str, password: str) -> tuple[bool, dict | None, str]:
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/register",
                json={'username': username, 'password': password},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 400:
                detail = response.json().get('detail', 'Пользователь с таким именем уже существует')
                return False, response.json(), detail

            if response.status_code == 422:
                return False, None, parse_v2_validation_errors(response)

            response.raise_for_status()
            data = response.json()
            return True, data, 'Пользователь зарегистрирован'

        except requests.RequestException as e:
            return False, None, f'Ошибка API: {e}'

    @staticmethod
    def logout(access_token: str) -> bool:
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/logout",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5
            )
            return response.status_code in (200, 204)
        except requests.RequestException:
            return False

    @staticmethod
    def get_current_user(access_token: str) -> dict | None:
        try:
            response = requests.get(
                f"{AuthController.BASE_URL}/me",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5
            )
            if response.status_code == 200:
                return response.json()
            return None
        except requests.RequestException:
            return None

    @staticmethod
    def refresh_token(refresh_token: str) -> tuple[bool, dict | None, str]:
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/refresh",
                json={'refresh_token': refresh_token},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 401:
                return False, None, 'Токен невалиден'

            if response.status_code == 422:
                return False, None, parse_v2_validation_errors(response)

            response.raise_for_status()
            data = response.json()
            return True, data, 'Токен обновлён'

        except requests.RequestException as e:
            return False, None, f'Ошибка API: {e}'

    @staticmethod
    def get_all_users(page: int = 1, size: int = 20, access_token: str = None) -> dict:
        headers = {'Authorization': f'Bearer {access_token}'} if access_token else {}
        try:
            response = requests.get(
                f"{AuthController.BASE_URL}/users",
                params={'page': page, 'size': size},
                headers=headers,
                timeout=10
            )
            response.raise_for_status()
            return normalize_api_response(response.json(), page)
        except requests.RequestException:
            return {'items': [], 'total': 0, 'page': page, 'pages': 1}

    @staticmethod
    def update_user_role(user_id: int, new_role: str, access_token: str = None) -> tuple[bool, dict | None, str]:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        } if access_token else {'Content-Type': 'application/json'}
        try:
            response = requests.put(
                f"{AuthController.BASE_URL}/{user_id}/role",
                json={'role': new_role},
                headers=headers,
                timeout=5
            )
            if response.status_code in (200, 204):
                return True, response.json(), 'Роль пользователя успешно обновлена'
            detail = response.json().get('detail', f'Ошибка API: {response.status_code}')
            return False, response.json(), detail
        except requests.RequestException as e:
            return False, None, f'Сбой подключения к API: {e}'
