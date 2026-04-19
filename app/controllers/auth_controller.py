# app/controllers/auth_controller.py
import requests
from django.conf import settings
import json

class AuthController:
    """Контроллер для работы с аутентификацией через API"""

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

            # ✅ Логируем ответ для отладки
            print(f"🔍 API Response: status={response.status_code}, body={response.text[:200]}")

            if response.status_code == 401:
                return False, None, 'Неверный логин или пароль'

            response.raise_for_status()

            # ✅ Безопасный парсинг JSON
            if not response.text.strip():
                return False, None, 'Пустой ответ от API'

            data = response.json()
            return True, data, 'Вход выполнен успешно'

        except json.JSONDecodeError as e:
            # ✅ Ловим ошибку парсинга JSON
            print(f"❌ JSONDecodeError: {e}, response text: {response.text}")
            return False, None, f'Невалидный ответ от API: {response.text[:100]}'

        except requests.RequestException as e:
            return False, None, f'Ошибка подключения к API: {e}'

    @staticmethod
    def register(username: str, password: str) -> tuple[bool, dict | None, str]:
        """
        Регистрация нового пользователя
        Returns: (success, user_data_or_errors, message)
        """
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/register",
                json={'username': username, 'password': password},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 400:
                return False, response.json(), 'Пользователь с таким именем уже существует'

            response.raise_for_status()
            data = response.json()

            return True, data, 'Пользователь зарегистрирован'

        except requests.RequestException as e:
            return False, None, f'Ошибка API: {e}'

    @staticmethod
    def logout(access_token: str) -> bool:
        """Выход из системы"""
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/logout",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5
            )
            return response.status_code == 200
        except requests.RequestException:
            return False

    @staticmethod
    def get_current_user(access_token: str) -> dict | None:
        """Получение информации о текущем пользователе"""
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
        """Обновление access токена"""
        try:
            response = requests.post(
                f"{AuthController.BASE_URL}/refresh",
                json={'refresh_token': refresh_token},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )

            if response.status_code == 401:
                return False, None, 'Токен невалиден'

            response.raise_for_status()
            data = response.json()

            return True, data, 'Токен обновлён'

        except requests.RequestException as e:
            return False, None, f'Ошибка API: {e}'