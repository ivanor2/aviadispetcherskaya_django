# app/views.py
import re
from datetime import date, time, datetime
from django.conf import settings
from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from app.controllers import (
    FlightController, PassengerController, BookingController, AuthController
)
from app.forms import (
    LoginForm, RegisterForm, FlightSearchForm, PassengerSearchForm, FlightForm
)
import requests


# ==========================================
# 🔧 Вспомогательные функции
# ==========================================

def _normalize_keys(data):
    """Рекурсивно преобразует camelCase ключи API в snake_case"""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            if k == 'id':
                result['id'] = v
            else:
                snake_key = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
                result[snake_key] = _normalize_keys(v)
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
    """Загружает карту {CODE: NAME} всех авиакомпаний"""
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
    """Загружает справочник всех аэропортов {ICAO: данные}, обходя пагинацию."""
    token = _get_token(request)
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    result = {}
    page = 1
    size = 100  # максимум, разрешённый API
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

def _parse_date(value):
    """Парсит строку даты 'YYYY-MM-DD' в объект date. Если уже date/datetime — возвращает как есть."""
    if isinstance(value, (date, datetime)):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value[:10], '%Y-%m-%d').date()
        except (ValueError, TypeError):
            pass
    return value


def _parse_time(value):
    """Парсит строку времени 'HH:MM:SS' или 'HH:MM' в объект time. Если уже time — возвращает как есть."""
    if isinstance(value, time):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.strptime(value[:5], '%H:%M').time()
        except (ValueError, TypeError):
            pass
    return value


def _enrich_flights_data(flights, airlines_map, airports_map):
    """
    Полное обогащение рейсов:
    1. Подставляет название авиакомпании
    2. Подставляет объекты аэропортов с названиями вместо кодов
    3. Гарантирует наличие *_name полей (чтобы шаблоны не падали и не показывали пустоту)
    4. Конвертирует строки даты/времени в объекты Python для корректной работы Django-фильтров
    """
    for flight in flights:
        if not flight:
            continue

        # --- Авиакомпания ---
        code = flight.get('airline_code', '').upper()
        flight['airline_name'] = airlines_map.get(code, code)

        # --- Аэропорты ---
        dep_icao = (flight.get('departure_airport_icao') or flight.get('departureAirportIcao', '')).strip().upper()
        arr_icao = (flight.get('arrival_airport_icao') or flight.get('arrivalAirportIcao', '')).strip().upper()


        dep_data = airports_map.get(dep_icao)
        arr_data = airports_map.get(arr_icao)


        # Если аэропорт не найден в мапе, создаем заглушку с кодом
        flight['departure_airport'] = dep_data or {'icao_code': dep_icao, 'name': dep_icao, 'city': '', 'country': ''}
        flight['arrival_airport'] = arr_data or {'icao_code': arr_icao, 'name': arr_icao, 'city': '', 'country': ''}

        # ✅ Имена аэропортов: берём name из справочника, если пустое — ICAO-код как запасной вариант
        flight['departure_airport_name'] = (flight['departure_airport'].get('name') or '').strip() or dep_icao
        flight['arrival_airport_name'] = (flight['arrival_airport'].get('name') or '').strip() or arr_icao

        # ✅ Конвертируем строки даты и времени в объекты Python,
        #    чтобы Django-фильтры |date:"d.m.Y" и |time:"H:i" работали корректно
        flight['departure_date'] = _parse_date(flight.get('departure_date'))
        flight['departure_time'] = _parse_time(flight.get('departure_time'))

    return flights


# ==========================================
# 🔐 АВТОРИЗАЦИЯ
# ==========================================

class LoginView(FormView):
    template_name = 'auth/login.html'
    form_class = LoginForm
    success_url = reverse_lazy('app:index')

    def get_success_url(self):
        return self.request.GET.get('next', self.success_url)

    def get(self, request, *args, **kwargs):
        if request.session.get('access_token'):
            return redirect(self.get_success_url())
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        success, tokens, message = AuthController.login(
            form.cleaned_data['username'], form.cleaned_data['password']
        )
        if not success:
            messages.error(self.request, message)
            return self.form_invalid(form)

        self.request.session['access_token'] = tokens.get('access_token')
        self.request.session['refresh_token'] = tokens.get('refreshToken', '')

        user_data = AuthController.get_current_user(tokens.get('access_token'))
        if user_data:
            self.request.session['user_info'] = user_data
            self.request.session['user_role'] = user_data.get('role', 'guest')

        messages.success(self.request, f'Добро пожаловать, {form.cleaned_data["username"]}!')
        return redirect(self.get_success_url())


class RegisterView(FormView):
    template_name = 'auth/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('app:login')

    def form_valid(self, form):
        success, data, message = AuthController.register(
            form.cleaned_data['username'], form.cleaned_data['password']
        )
        if not success:
            detail = data.get('detail', message) if isinstance(data, dict) else message
            messages.error(self.request, detail)
            return self.form_invalid(form)

        messages.success(self.request, 'Регистрация успешна! Войдите в систему.')
        return redirect('app:login')


class LogoutView(View):
    def get(self, request):
        token = request.session.get('access_token')
        if token:
            AuthController.logout(token)
        request.session.flush()
        messages.success(request, 'Вы вышли из системы')
        return redirect('app:login')


# ==========================================
# 🏠 ГЛАВНАЯ И СПИСКИ
# ==========================================

class IndexView(TemplateView):
    template_name = 'index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        token = _get_token(self.request)

        try:
            flights_meta = FlightController.get_all_flights(page=1, size=1, access_token=token)
            passengers_meta = PassengerController.get_all_passengers(page=1, size=1, access_token=token)
            recent_data = FlightController.get_all_flights(page=1, size=6, access_token=token)

            flights_items = flights_meta.get('items', [])
            active_flights = sum(1 for f in flights_items if f.get('freeSeats', f.get('free_seats', 0)) > 0)

            recent_flights = _normalize_keys(recent_data.get('items', []))

            # Загружаем справочники
            airlines_map = _fetch_airlines_map(self.request)
            airports_map = _fetch_airports_map(self.request)

            # ✅ Обогащаем данные
            recent_flights_enriched = _enrich_flights_data(recent_flights, airlines_map, airports_map)

            context.update({
                'total_flights': flights_meta.get('total', 0),
                'total_passengers': passengers_meta.get('total', 0),
                'active_flights': active_flights,
                'total_bookings': 0,
                'recent_flights': recent_flights_enriched
            })
        except Exception:
            context.update({
                'total_flights': 0, 'total_passengers': 0,
                'active_flights': 0, 'total_bookings': 0, 'recent_flights': []
            })
        return context


class FlightListView(TemplateView):
    template_name = 'flights/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        token = _get_token(self.request)

        page_num = self.request.GET.get('page', 1)
        try:
            page_num = int(page_num)
        except (ValueError, TypeError):
            page_num = 1

        search_form = FlightSearchForm(self.request.GET)
        items, total, api_pages = [], 0, 1

        # 1. Получение данных
        if search_form.is_valid():
            query = search_form.cleaned_data.get('query', '').strip()
            if query:
                stype = search_form.cleaned_data.get('search_type')
                if stype == 'number':
                    data = FlightController.get_flight_with_passengers(query.upper(), token)
                    items = [data['flight']] if data.get('flight') else []
                elif stype == 'arrival':
                    items = FlightController.search_by_arrival(query, token)
                total = len(items)
                api_pages = max(1, (total + 9) // 10)
            else:
                data = FlightController.get_all_flights(page=page_num, size=10, access_token=token)
                items = data.get('items', [])
                total = data.get('total', 0)
                api_pages = data.get('pages', 1)
        else:
            data = FlightController.get_all_flights(page=page_num, size=10, access_token=token)
            items = data.get('items', [])
            total = data.get('total', 0)
            api_pages = data.get('pages', 1)

        # 2. Нормализация и обогащение
        normalized_items = _normalize_keys(items)

        # ✅ Загружаем справочники
        airlines_map = _fetch_airlines_map(self.request)
        airports_map = _fetch_airports_map(self.request)

        # ✅ Обогащаем данные именами и конвертируем даты
        enriched_items = _enrich_flights_data(normalized_items, airlines_map, airports_map)

        # 3. Пагинация
        page_obj = {
            'object_list': enriched_items,
            'number': data.get('page', page_num),
            'has_previous': page_num > 1,
            'previous_page_number': max(1, page_num - 1),
            'has_next': page_num < api_pages,
            'next_page_number': min(page_num + 1, api_pages),
            'paginator': {'num_pages': api_pages}
        }

        context.update({
            'flights': page_obj['object_list'],
            'page_obj': page_obj,
            'is_paginated': total > 10,
            'search_form': search_form
        })
        return context


class FlightSearchView(FormView):
    form_class = FlightSearchForm
    template_name = 'flights/list.html'

    def form_valid(self, form):
        return redirect(
            f"{reverse_lazy('app:flight_list')}?search_type={form.cleaned_data['search_type']}&query={form.cleaned_data['query']}"
        )


class FlightCreateView(FormView):
    template_name = 'flights/form.html'
    form_class = FlightForm
    success_url = reverse_lazy('app:flight_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        context['title'] = 'Новый авиарейс'
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['access_token'] = _get_token(self.request)
        return kwargs

    def form_valid(self, form):
        airline_code = form.cleaned_data['airline']
        numeric_part = form.cleaned_data['flight_number']

        full_flight_number = f"{airline_code}-{numeric_part}"

        payload = {
            'flightNumber': full_flight_number,
            'airlineCode': airline_code,
            'departureAirportIcao': form.cleaned_data['departure_airport'],
            'arrivalAirportIcao': form.cleaned_data['arrival_airport'],
            'departureDate': str(form.cleaned_data['departure_date']),
            'departureTime': str(form.cleaned_data['departure_time']),
            'totalSeats': form.cleaned_data['total_seats'],
            'freeSeats': form.cleaned_data.get('free_seats', form.cleaned_data['total_seats'])
        }

        success, data, message = FlightController.create_flight(payload, _get_token(self.request))
        if success:
            messages.success(self.request, message)
            return super().form_valid(form)

        messages.error(self.request, message)
        return self.form_invalid(form)


class FlightDetailView(TemplateView):
    """Детали рейса"""
    template_name = 'flights/detail.html'

    def get(self, request, *args, **kwargs):
        token = request.session.get('access_token')
        flight_id = kwargs.get('pk')
        flight_data = FlightController.get_flight_by_id(flight_id, token)

        if not flight_data:
            messages.error(request, 'Рейс не найден')
            return redirect('app:flight_list')

        self._cached_flight_data = flight_data
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))

        token = self.request.session.get('access_token')
        flight_id = kwargs.get('pk')

        flight_data = getattr(self, '_cached_flight_data', None)
        if flight_data is None:
            flight_data = FlightController.get_flight_by_id(flight_id, token)

        if not flight_data:
            messages.error(self.request, 'Рейс не найден')
            return context

        flight_number = flight_data.get('flightNumber')
        full_data = FlightController.get_flight_with_passengers(flight_number, token)
        flight_data = full_data.get('flight', flight_data)
        passengers_data = full_data.get('passengers', [])

        airlines_map = _fetch_airlines_map(self.request)
        airports_map = _fetch_airports_map(self.request)

        flight_normalized = _normalize_keys(flight_data)
        enriched_flights = _enrich_flights_data([flight_normalized], airlines_map, airports_map)

        flight_enriched = enriched_flights[0] if enriched_flights else None

        context.update({
            'flight': flight_enriched,
            'passengers': _normalize_keys(passengers_data)
        })
        return context


class FlightDeleteView(View):
    def post(self, request, pk):
        token = request.session.get('access_token')
        success = FlightController.delete_flight(pk, token)
        if success:
            messages.success(request, 'Рейс успешно удалён')
        else:
            messages.error(request, 'Ошибка при удалении рейса')
        return redirect('app:flight_list')


# ==========================================
# 👥 ПАССАЖИРЫ И БРОНИРОВАНИЯ
# ==========================================

class PassengerListView(TemplateView):
    template_name = 'passengers/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        token = _get_token(self.request)
        page_num = self.request.GET.get('page', 1)
        search_type = self.request.GET.get('search_type', 'passport')
        query = self.request.GET.get('query', '').strip()

        items = []
        try:
            if query:
                if search_type == 'passport':
                    items = PassengerController.search_by_passport(query, token)
                else:
                    items = PassengerController.search_by_name(query, token)
            else:
                data = PassengerController.get_all_passengers(page=page_num, size=10, access_token=token)
                items = data.get('items', [])
        except Exception:
            pass

        paginator = Paginator(_normalize_keys(items), 10)
        try:
            page_obj = paginator.page(page_num)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        context.update({
            'passengers': page_obj.object_list,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'search_form': {'search_type': search_type, 'query': query}
        })
        return context


class PassengerSearchView(FormView):
    template_name = 'passengers/search.html'
    form_class = PassengerSearchForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        return context

    def form_valid(self, form):
        stype = form.cleaned_data['search_type']
        query = form.cleaned_data['query']
        token = _get_token(self.request)
        result = None
        try:
            items = PassengerController.search_by_passport(query,
                                                           token) if stype == 'passport' else PassengerController.search_by_name(
                query, token)
            result = items[0] if items else None
        except Exception:
            pass

        if result:
            messages.success(self.request, 'Пассажир найден')
            return render(self.request, 'passengers/search.html', {
                'passenger': _normalize_keys(result),
                'search_form': form,
                **_get_role_perms(self.request)
            })
        messages.error(self.request, 'Пассажир не найден')
        return self.form_invalid(form)


class BookingCreateView(FormView):
    template_name = 'bookings/create.html'
    success_url = reverse_lazy('app:index')

    def get_form_class(self):
        from app.forms import BookingForm
        return BookingForm

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        flight_id = self.kwargs.get('flight_id')
        token = _get_token(self.request)
        context['flight'] = FlightController.get_flight_by_id(flight_id, token)
        if context['flight']:
            context['flight'] = _normalize_keys(context['flight'])
        return context

    def form_valid(self, form):
        flight_id = self.kwargs.get('flight_id')
        passenger_id = form.cleaned_data['passenger'].id if hasattr(form.cleaned_data['passenger'], 'id') else \
        form.cleaned_data['passenger']
        payload = {'flightId': flight_id, 'passengerId': passenger_id}
        success, data, message = BookingController.create_booking(payload, _get_token(self.request))

        if success:
            messages.success(self.request, message)
            return redirect('app:flight_detail', pk=flight_id)
        messages.error(self.request, message)
        return self.form_invalid(form)


class BookingCancelView(View):
    def post(self, request, booking_id):
        token = _get_token(request)
        success = BookingController.cancel_booking(booking_id, token)
        if success:
            messages.success(request, 'Билет успешно возвращён')
        else:
            messages.error(request, 'Не удалось отменить бронирование')
        flight_id = request.POST.get('flight_id')
        return redirect('app:flight_detail', pk=flight_id) if flight_id else redirect('app:flight_list')