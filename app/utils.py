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

# ==========================================
# 🔧 Вспомогательные функции для Views
# ==========================================

def _normalize_keys(data):
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k == 'id':
                result['id'] = v
            else:
                snake_key = ''.join(['_' + c.lower() if c.isupper() else c for c in k]).lstrip('_')
                result[snake_key] = _normalize_keys(v) if isinstance(v, (dict, list)) else v
        return result
    elif isinstance(data, list):
        return [_normalize_keys(item) for item in data]
    return data


def _get_token(request):
    return request.session.get('access_token')


def _get_role_perms(request):
    role = request.session.get('user_role', 'guest')
    return {
        'user_role': role,
        'can_manage_flights': role in ['admin', 'dispatcher'],
        'can_manage_passengers': role in ['admin', 'dispatcher'],
        'can_manage_bookings': role in ['admin', 'dispatcher'],
        'can_manage_airports': role == 'admin',
        'can_view_reports': role in ['admin', 'dispatcher'],
        'can_manage_users': role == 'admin',
    }


def _fetch_airlines_map(request):
    token = _get_token(request)
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        resp = requests.get(f"{settings.API_BASE_URL}/airlines", headers=headers, timeout=5)
        if resp.status_code == 200:
            return {a.get('code', '').upper(): a.get('name', '') for a in resp.json()}
    except Exception:
        pass
    return {}


def _fetch_airports_map(request):
    token = _get_token(request)
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    result = {}
    page = 1
    size = 100
    try:
        while True:
            resp = requests.get(
                f"{settings.API_BASE_URL}/airports",
                params={'page': page, 'size': size},
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                break
            data = resp.json()
            items = data.get('items', [])
            for a in items:
                icao = (a.get('icao_code') or a.get('icaoCode') or '').strip().upper()
                if icao:
                    result[icao] = a
            total_pages = data.get('pages', 1)
            if page >= total_pages:
                break
            page += 1
    except Exception:
        pass
    return result


def _parse_datetime_safe(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date) and not isinstance(value, datetime):
        return datetime.combine(value, time.min)
    if isinstance(value, str) and value:
        try:
            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S.%f', '%Y-%m-%d %H:%M']:
                try:
                    return datetime.strptime(value[:19].replace('Z', ''), fmt.replace('.%f', '') if '.' not in fmt else fmt)
                except ValueError:
                    continue
            return datetime.strptime(value[:10], '%Y-%m-%d')
        except (ValueError, TypeError):
            pass
    return None

def _parse_time(value):
    if isinstance(value, time):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value[:5], '%H:%M').time()
        except (ValueError, TypeError):
            pass
    return value


def _enrich_flights_data(flights, airlines_map, airports_map):
    for flight in flights:
        if not flight:
            continue

        code = flight.get('airline_code', '').upper()
        flight['airline_name'] = airlines_map.get(code, code)

        dep_icao = (flight.get('departure_airport_icao') or flight.get('departureAirportIcao', '')).strip().upper()
        arr_icao = (flight.get('arrival_airport_icao') or flight.get('arrivalAirportIcao', '')).strip().upper()

        dep_data = airports_map.get(dep_icao)
        arr_data = airports_map.get(arr_icao)

        flight['departure_airport'] = dep_data or {'icao_code': dep_icao, 'name': dep_icao, 'city': '', 'country': ''}
        flight['arrival_airport'] = arr_data or {'icao_code': arr_icao, 'name': arr_icao, 'city': '', 'country': ''}

        flight['departure_airport_name'] = (flight['departure_airport'].get('name') or '').strip() or dep_icao
        flight['arrival_airport_name'] = (flight['arrival_airport'].get('name') or '').strip() or arr_icao

        flight['departure_date'] = _parse_datetime_safe(flight.get('departure_date'))
        flight['departure_time'] = _parse_time(flight.get('departure_time'))

    return flights


def _enrich_bookings_with_flight_numbers(bookings: list, access_token: str) -> list:
    from app.controllers import FlightController
    enriched = []
    for b in bookings:
        flight_id = b.get('flight_id') or b.get('flightId')
        if flight_id:
            flight_info = FlightController.get_flight_short_info(flight_id, access_token)
            if flight_info:
                b['flight_number'] = flight_info.get('flight_number')
                b['departure_icao'] = flight_info.get('departure_airport_icao')
                b['arrival_icao'] = flight_info.get('arrival_airport_icao')
        enriched.append(_normalize_keys(b))
    return enriched