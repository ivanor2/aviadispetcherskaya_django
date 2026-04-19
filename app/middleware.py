# app/middleware.py
from django.shortcuts import redirect
import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AuthMiddleware:
    """Middleware для принудительной проверки аутентификации через API"""

    # Публичные пути, доступные БЕЗ авторизации
    # Убрана главная страница '/', теперь она требует логина
    EXEMPT_PATHS = ['/login/', '/register/', '/static/', '/media/', '/admin/']

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Пропускаем публичные URL и статические файлы (чтобы не было циклов редиректов)
        if request.path in self.EXEMPT_PATHS or request.path.startswith('/static/') or request.path.startswith(
                '/media/'):
            return self.get_response(request)

        access_token = request.session.get('access_token')

        # 2. Если токена нет в сессии — сразу кидаем на логин
        if not access_token:
            return redirect('app:login')

        # 3. Проверяем валидность токена через внешний API
        try:
            response = requests.get(
                f"{settings.API_BASE_URL}/auth/me",
                headers={'Authorization': f'Bearer {access_token}'},
                timeout=5
            )

            if response.status_code == 401:
                logger.info("Токен невалиден, очистка сессии")
                request.session.flush()
                return redirect('app:login')

            # Обновляем данные пользователя в сессии
            user_data = response.json()
            request.session['user_info'] = user_data
            request.session['user_role'] = user_data.get('role', 'guest')

        except requests.RequestException as e:
            logger.warning(f"⚠️ Ошибка проверки токена API: {e}")
            # При сбое API не блокируем пользователя, но при следующем запросе проверка повторится

        return self.get_response(request)