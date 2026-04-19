# app/views.py
import re
import requests
from django.conf import settings
from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from app.forms import (
    LoginForm, RegisterForm, FlightSearchForm, PassengerSearchForm,
    FlightForm, BookingForm
)


# ==========================================
# 🔧 Вспомогательные функции
# ==========================================

# app/views.py

def _normalize_keys(data):
    """Рекурсивно преобразует camelCase ключи API в snake_case для шаблонов Django"""
    if isinstance(data, dict):
        result = {}
        for k, v in data.items():
            # ✅ Особая обработка для 'id' - гарантированно сохраняем
            if k == 'id':
                result['id'] = v
            else:
                # Конвертируем camelCase в snake_case: flightNumber → flight_number
                snake_key = re.sub(r'(?<!^)(?=[A-Z])', '_', k).lower()
                result[snake_key] = _normalize_keys(v)
        return result
    elif isinstance(data, list):
        return [_normalize_keys(item) for item in data]
    return data


def _get_headers(request):
    """Возвращает заголовки с токеном авторизации"""
    token = request.session.get('access_token')
    return {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'} if token else {}


def _get_role_perms(request):
    """Генерирует флаги прав доступа на основе роли из сессии"""
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


def _fetch_airports_map(request):
    """Загружает все аэропорты и возвращает словарь {icao_code: {...}}"""
    headers = _get_headers(request)
    try:
        # ✅ size=200 достаточно для аэропортов и не вызывает 422
        resp = requests.get(f"{settings.API_BASE_URL}/airports", params={'page': 1, 'size': 100}, headers=headers, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            return {a['icao_code']: a for a in items}
    except requests.RequestException:
        pass
    return {}



def _enrich_flights_with_airports(flights, airports_map):
    """
    Добавляет к каждому рейсу объекты departure_airport и arrival_airport
    на основе ICAO-кодов.
    """
    for flight in flights:
        dep_icao = flight.get('departure_airport_icao')
        arr_icao = flight.get('arrival_airport_icao')

        flight['departure_airport'] = airports_map.get(dep_icao, {
            'icao_code': dep_icao, 'name': 'Неизвестно', 'city': '', 'country': ''
        })
        flight['arrival_airport'] = airports_map.get(arr_icao, {
            'icao_code': arr_icao, 'name': 'Неизвестно', 'city': '', 'country': ''
        })
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
        try:
            resp = requests.post(
                f"{settings.API_BASE_URL}/auth/login",
                json={'username': form.cleaned_data['username'], 'password': form.cleaned_data['password']},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            if resp.status_code == 401:
                messages.error(self.request, 'Неверный логин или пароль')
                return self.form_invalid(form)

            tokens = resp.json()
            self.request.session['access_token'] = tokens.get('access_token')
            self.request.session['refresh_token'] = tokens.get('refreshToken', '')

            # Получаем профиль
            me = requests.get(f"{settings.API_BASE_URL}/auth/me", headers=_get_headers(self.request), timeout=5)
            if me.status_code == 200:
                user_info = me.json()
                self.request.session['user_info'] = user_info
                self.request.session['user_role'] = user_info.get('role', 'guest')

            messages.success(self.request, f'Добро пожаловать, {form.cleaned_data["username"]}!')
            return redirect(self.get_success_url())
        except requests.RequestException as e:
            messages.error(self.request, f'Ошибка подключения к API: {e}')
            return self.form_invalid(form)


class RegisterView(FormView):
    template_name = 'auth/register.html'
    form_class = RegisterForm
    success_url = reverse_lazy('app:login')

    def form_valid(self, form):
        try:
            resp = requests.post(
                f"{settings.API_BASE_URL}/auth/register",
                json={'username': form.cleaned_data['username'], 'password': form.cleaned_data['password']},
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            if resp.status_code == 400:
                data = resp.json()
                detail = data.get('detail', 'Ошибка валидации')
                messages.error(self.request, detail)
                return self.form_invalid(form)

            messages.success(self.request, 'Регистрация успешна! Войдите в систему.')
            return redirect('app:login')
        except requests.RequestException as e:
            messages.error(self.request, f'Ошибка подключения к API: {e}')
            return self.form_invalid(form)


class LogoutView(View):
    def get(self, request):
        token = request.session.get('access_token')
        if token:
            try:
                requests.post(f"{settings.API_BASE_URL}/auth/logout", headers=_get_headers(request), timeout=5)
            except requests.RequestException:
                pass
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
        headers = _get_headers(self.request)

        try:
            # Статистика рейсов
            flights_meta = requests.get(f"{settings.API_BASE_URL}/flights", params={'page': 1, 'size': 1},
                                        headers=headers, timeout=5).json()
            total_flights = flights_meta.get('total', 0)

            # Загружаем все рейсы для подсчёта активных и получения последних 6
            flights_data = requests.get(f"{settings.API_BASE_URL}/flights", params={'page': 1, 'size': 100},
                                        headers=headers, timeout=10).json()
            flights_items = flights_data.get('items', [])

            # Считаем активные (где freeSeats > 0)
            active_flights = sum(1 for f in flights_items if f.get('freeSeats', 0) > 0)

            # Последние 6 рейсов
            recent_data = requests.get(f"{settings.API_BASE_URL}/flights", params={'page': 1, 'size': 6},
                                       headers=headers, timeout=10).json()
            recent_flights = recent_data.get('items', [])

            # Статистика пассажиров
            passengers_meta = requests.get(f"{settings.API_BASE_URL}/passengers", params={'page': 1, 'size': 1},
                                           headers=headers, timeout=5).json()
            total_passengers = passengers_meta.get('total', 0)

            # Статистика бронирований
            bookings_meta = requests.get(f"{settings.API_BASE_URL}/bookings", params={'page': 1, 'size': 1},
                                         headers=headers, timeout=5).json()
            total_bookings = bookings_meta.get('total', 0)

            # Обогащаем последние рейсы данными об аэропортах
            airports_map = _fetch_airports_map(self.request)
            recent_flights_normalized = _normalize_keys(recent_flights)
            recent_flights_enriched = _enrich_flights_with_airports(recent_flights_normalized, airports_map)

            context.update({
                'total_flights': total_flights,
                'total_passengers': total_passengers,
                'active_flights': active_flights,
                'total_bookings': total_bookings,
                'recent_flights': recent_flights_enriched
            })


        except requests.RequestException:
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
        page_num = self.request.GET.get('page', 1)
        search_form = FlightSearchForm(self.request.GET)

        items, total = [], 0
        headers = _get_headers(self.request)

        try:
            if search_form.is_valid():
                stype = search_form.cleaned_data.get('search_type')
                query = search_form.cleaned_data.get('query', '').strip()

                if stype == 'number' and query:
                    res = requests.get(f"{settings.API_BASE_URL}/flights/by-number/{query.upper()}", headers=headers,
                                       timeout=5)

                    if res.status_code == 200:
                        json_data = res.json()
                        flight_obj = json_data.get('flight')

                        if flight_obj:
                            items = [flight_obj]  # В список кладём только сам рейс
                            total = 1
                        else:
                            items = []
                            total = 0
                            messages.warning(self.request, 'Рейс найден, но данные о нем пусты')

                    elif res.status_code == 404:
                        items, total = [], 0
                        messages.warning(self.request, 'Рейс не найден')
                    else:
                        res.raise_for_status()

                elif stype == 'arrival' and query:
                    res = requests.get(f"{settings.API_BASE_URL}/flights/search/by-arrival/{query}", headers=headers,
                                       timeout=5)
                    if res.status_code == 200:
                        items = res.json()  # API возвращает список
                        total = len(items)
                    else:
                        res.raise_for_status()
                else:
                    # Обычный список с пагинацией
                    res = requests.get(f"{settings.API_BASE_URL}/flights", params={'page': page_num, 'size': 10},
                                       headers=headers, timeout=5)
                    res.raise_for_status()
                    data = res.json()
                    items = data.get('items', [])
                    total = data.get('total', 0)
            else:
                # Форма не валидна или пустая → грузим обычный список
                res = requests.get(f"{settings.API_BASE_URL}/flights", params={'page': page_num, 'size': 10},
                                   headers=headers, timeout=5)
                res.raise_for_status()
                data = res.json()
                items = data.get('items', [])
                total = data.get('total', 0)

        except requests.HTTPError as e:
            print(f"🔴 HTTP Error: {e.response.status_code} - {e.response.text}")
            messages.error(self.request, f'Ошибка API: {e.response.status_code}')
        except requests.RequestException as e:
            print(f"🔴 Network Error: {e}")
            messages.error(self.request, 'Нет связи с сервером рейсов')

        # 🔍 Отладка в консоли Django
        print(f"🟢 Flights API: got {len(items)} items, total={total}")
        if items:
            print(f"🔑 Keys: {list(items[0].keys())}")

        paginator = Paginator(_normalize_keys(items), 10)
        try:
            page_obj = paginator.page(page_num)
        except (PageNotAnInteger, EmptyPage):
            page_obj = paginator.page(1)

        context.update({
            'flights': page_obj.object_list,
            'page_obj': page_obj,
            'is_paginated': page_obj.has_other_pages(),
            'search_form': search_form
        })
        return context


class FlightSearchView(FormView):
    """Перенаправляет на FlightListView с параметрами поиска"""
    form_class = FlightSearchForm
    template_name = 'flights/list.html'

    def form_valid(self, form):
        query_params = {
            'search_type': form.cleaned_data['search_type'],
            'query': form.cleaned_data['query']
        }
        return redirect(
            f"{reverse_lazy('app:flight_list')}?search_type={query_params['search_type']}&query={query_params['query']}")


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
        # Передаём токен из сессии в аргументы формы
        kwargs['access_token'] = self.request.session.get('access_token')
        return kwargs

    def form_valid(self, form):
        dep_airport = form.cleaned_data['departure_airport']
        arr_airport = form.cleaned_data['arrival_airport']

        # ✅ КРИТИЧНО: отправляем ICAO-коды вместо ID
        payload = {
            'flightNumber': form.cleaned_data['flight_number'],
            'airlineName': form.cleaned_data['airline_name'],
            'departureAirportIcao': form.cleaned_data['departure_airport'],  # Теперь это строка 'UUSS'
            'arrivalAirportIcao': form.cleaned_data['arrival_airport'],  # Теперь это строка 'UUEE'
            'departureDate': str(form.cleaned_data['departure_date']),
            'departureTime': str(form.cleaned_data['departure_time']),
            'totalSeats': form.cleaned_data['total_seats'],
            'freeSeats': form.cleaned_data.get('free_seats', form.cleaned_data['total_seats'])
        }

        try:
            resp = requests.post(
                f"{settings.API_BASE_URL}/flights",
                json=payload,
                headers=_get_headers(self.request),
                timeout=10
            )
            if resp.status_code in (200, 201):
                messages.success(self.request, f'Рейс {payload["flightNumber"]} успешно создан')
                return super().form_valid(form)
            else:
                detail = resp.json().get('detail', 'Ошибка API')
                messages.error(self.request, detail)
        except requests.RequestException as e:
            messages.error(self.request, f'Ошибка подключения: {e}')

        return self.form_invalid(form)


class FlightDetailView(TemplateView):
    template_name = 'flights/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        headers = _get_headers(self.request)
        flight_id = kwargs.get('pk')

        try:
            # ✅ ИСПРАВЛЕНО: используем endpoint /by-number для получения пассажиров
            # Но сначала нам нужно получить flight_number. Запросим по ID.
            flight_resp = requests.get(f"{settings.API_BASE_URL}/flights/{flight_id}", headers=headers, timeout=5)

            if flight_resp.status_code == 200:
                flight_data = flight_resp.json()
                flight_number = flight_data.get('flightNumber')

                # Получаем рейс с пассажирами по номеру
                flight_with_pax_resp = requests.get(f"{settings.API_BASE_URL}/flights/by-number/{flight_number}",
                                                    headers=headers, timeout=5)

                if flight_with_pax_resp.status_code == 200:
                    full_data = flight_with_pax_resp.json()
                    flight_data = full_data.get('flight', flight_data)
                    passengers_data = full_data.get('passengers', [])
                else:
                    passengers_data = []

                # Обогащаем аэропортами
                airports_map = _fetch_airports_map(self.request)
                flight_normalized = _normalize_keys(flight_data)
                flight_enriched = _enrich_flights_with_airports([flight_normalized], airports_map)[0]

                context['flight'] = flight_enriched
                context['passengers'] = _normalize_keys(passengers_data)
            else:
                messages.error(self.request, 'Рейс не найден')
                return redirect('app:flight_list')

        except requests.RequestException as e:
            messages.error(self.request, f'Ошибка API: {e}')
            return redirect('app:flight_list')

        return context


# ==========================================
# 👥 ПАССАЖИРЫ
# ==========================================

class PassengerListView(TemplateView):
    template_name = 'passengers/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        page_num = self.request.GET.get('page', 1)
        search_type = self.request.GET.get('search_type', 'passport')
        query = self.request.GET.get('query', '').strip()
        items = []
        headers = _get_headers(self.request)

        try:
            if query:
                if search_type == 'passport':
                    res = requests.get(f"{settings.API_BASE_URL}/passengers/search/by-passport/{query}",
                                       headers=headers, timeout=5)
                    if res.status_code == 200:
                        items = [res.json()]
                else:
                    res = requests.get(f"{settings.API_BASE_URL}/passengers/search/by-name/{query}", headers=headers,
                                       timeout=5)
                    if res.status_code == 200:
                        items = res.json()
            else:
                res = requests.get(f"{settings.API_BASE_URL}/passengers", params={'page': page_num, 'size': 10},
                                   headers=headers, timeout=5)
                if res.status_code == 200:
                    data = res.json()
                    items = data.get('items', [])
        except requests.RequestException:
            pass

        # Подсчитываем бронирования для каждого пассажира
        for p in items:
            try:
                p.setdefault('bookings_count', 0)
                # Можно добавить запрос к API для получения count, пока оставляем 0 или добавляем позже
            except:
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
        headers = _get_headers(self.request)
        result = None

        try:
            if stype == 'passport':
                resp = requests.get(f"{settings.API_BASE_URL}/passengers/search/by-passport/{query}", headers=headers,
                                    timeout=5)
                if resp.status_code == 200:
                    result = _normalize_keys(resp.json())
            else:
                resp = requests.get(f"{settings.API_BASE_URL}/passengers/search/by-name/{query}", headers=headers,
                                    timeout=5)
                if resp.status_code == 200 and resp.json():
                    result = _normalize_keys(resp.json()[0])
        except requests.RequestException:
            pass

        if result:
            messages.success(self.request, 'Пассажир найден')
            return render(self.request, 'passengers/search.html', {'passenger': result, 'search_form': form})
        messages.error(self.request, 'Пассажир не найден')
        return self.form_invalid(form)


# ==========================================
# 🎫 БРОНИРОВАНИЯ
# ==========================================

class BookingCreateView(FormView):
    template_name = 'bookings/create.html'
    form_class = BookingForm
    success_url = reverse_lazy('app:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        flight_id = self.kwargs.get('flight_id')
        headers = _get_headers(self.request)
        try:
            resp = requests.get(f"{settings.API_BASE_URL}/flights/{flight_id}", headers=headers, timeout=5)
            context['flight'] = _normalize_keys(resp.json()) if resp.status_code == 200 else None
        except requests.RequestException:
            context['flight'] = None
        return context

    def form_valid(self, form):
        flight_id = self.kwargs.get('flight_id')
        passenger_id = form.cleaned_data['passenger'].id if hasattr(form.cleaned_data['passenger'], 'id') else \
        form.cleaned_data['passenger']

        payload = {
            'flightId': flight_id,
            'passengerId': passenger_id
        }
        try:
            resp = requests.post(f"{settings.API_BASE_URL}/bookings/", json=payload, headers=_get_headers(self.request),
                                 timeout=10)
            if resp.status_code == 201:
                booking = resp.json()
                messages.success(self.request, f'Билет оформлен! Код: {booking.get("bookingCode")}')
                return redirect('app:flight_detail', pk=flight_id)
            else:
                messages.error(self.request, resp.json().get('detail', 'Ошибка оформления'))
        except requests.RequestException as e:
            messages.error(self.request, f'Сбой API: {e}')
        return self.form_invalid(form)


class BookingCancelView(View):
    def post(self, request, booking_id):
        try:
            resp = requests.delete(f"{settings.API_BASE_URL}/bookings/{booking_id}", headers=_get_headers(request),
                                   timeout=10)
            if resp.status_code == 204:
                messages.success(request, 'Билет успешно возвращён')
            else:
                messages.error(request, 'Не удалось отменить бронирование')
        except requests.RequestException:
            messages.error(request, 'Сбой соединения с API')

        flight_id = request.POST.get('flight_id')
        return redirect('app:flight_detail', pk=flight_id) if flight_id else redirect('app:flight_list')