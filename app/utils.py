# app/controllers/utils.py
import requests
import logging

logger = logging.getLogger(__name__)


def normalize_api_response(response_data: dict | list, page: int = 1) -> dict:
    """
    Универсальная нормализация ответа от FastAPI.
    Работает с:
    - v1: возвращает простой список [...]
    - v2: возвращает пагинированный объект {"items": [...], "total": N, "page": 1, "pages": 10}
    """
    if isinstance(response_data, list):
        return {
            'items': response_data,
            'total': len(response_data),
            'page': page,
            'pages': 1,
            'has_next': False,
            'has_previous': False
        }

    if isinstance(response_data, dict):
        items = response_data.get('items', response_data.get('data', []))
        total = response_data.get('total', len(items))
        pages = response_data.get('pages', response_data.get('total_pages', 1))
        current_page = response_data.get('page', response_data.get('current_page', page))

        return {
            'items': items,
            'total': total,
            'page': current_page,
            'pages': pages,
            'has_next': current_page < pages,
            'has_previous': current_page > 1
        }

    return {'items': [], 'total': 0, 'page': page, 'pages': 1}


def parse_v2_validation_errors(response: requests.Response) -> str:
    """
    Превращает 422 ошибку от FastAPI v2 в читаемую строку для Django messages.
    Пример: "passportNumber: формат должен быть NNNN-NNNNNN"
    """
    if response.status_code != 422:
        try:
            return response.json().get('detail', f'Ошибка {response.status_code}')
        except (ValueError, KeyError):
            return f'Ошибка {response.status_code}'

    try:
        errors = response.json().get('detail', [])
        if isinstance(errors, list):
            messages = []
            for err in errors:
                if isinstance(err, dict):
                    loc = err.get('loc', [])
                    field = loc[-1] if len(loc) > 1 else loc[0] if loc else 'Поле'
                    msg = err.get('msg', 'Ошибка валидации')
                    messages.append(f"{field}: {msg}")
            return "\n".join(messages) if messages else "Ошибка валидации данных"
        return str(errors)
    except Exception as e:
        logger.warning(f"Failed to parse validation error: {e}")
        return "Ошибка валидации данных"


def safe_api_call(func, *args, default=None, **kwargs):
    """
    Декоратор-обёртка для безопасного вызова API-методов.
    Возвращает default при любой ошибке подключения.
    """
    try:
        return func(*args, **kwargs)
    except requests.RequestException as e:
        logger.warning(f"API call failed: {e}")
        return default
    except Exception as e:
        logger.error(f"Unexpected error in API call: {e}")
        return default

def parse_v2_errors(response) -> str:
    """Превращает 422 ошибку FastAPI в читаемую строку"""
    if response.status_code == 422:
        try:
            errors = response.json().get('detail', [])
            msgs = [f"{e.get('loc', [''])[1]}: {e.get('msg', '')}" for e in errors if isinstance(e, dict)]
            return "\n".join(msgs)
        except Exception:
            pass
    try:
        return response.json().get('detail', f'Ошибка {response.status_code}')
    except ValueError:
        return f'Ошибка {response.status_code}'