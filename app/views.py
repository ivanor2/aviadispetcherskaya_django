import re
from django.conf import settings
from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from app.controllers import (
    FlightController,
    PassengerController,
    BookingController,
    AuthController
)
from app.forms import (
    LoginForm, RegisterForm, FlightSearchForm, PassengerSearchForm,
    FlightForm
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


def _fetch_airports_map(request):
    token = _get_token(request)
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    try:
        resp = requests.get(f"{settings.API_BASE_URL}/airports", params={'page': 1, 'size': 200}, headers=headers,
                            timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            items = data.get('items', [])
            # Поддерживаем оба формата ключей от API
            return {a.get('icaoCode', a.get('icao_code', '')): _normalize_keys(a) for a in items}
    except requests.RequestException:
        pass
    return {}


def _enrich_flights_with_airports(flights, airports_map):
    """Добавляет к каждому рейсу объекты departure_airport и arrival_airport"""
    result = []
    for flight in flights:
        # ✅ Пропускаем None значения
        if flight is None:
            result.append(None)
            continue

        dep_icao = flight.get('departure_airport_icao')
        arr_icao = flight.get('arrival_airport_icao')

        flight['departure_airport'] = airports_map.get(dep_icao, {
            'icao_code': dep_icao, 'name': 'Неизвестно', 'city': '', 'country': ''
        })
        flight['arrival_airport'] = airports_map.get(arr_icao, {
            'icao_code': arr_icao, 'name': 'Неизвестно', 'city': '', 'country': ''
        })
        result.append(flight)
    return result


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
            flights_page = FlightController.get_all_flights(page=1, size=100, access_token=token)
            recent_data = FlightController.get_all_flights(page=1, size=6, access_token=token)

            flights_items = flights_page.get('items', [])
            active_flights = sum(1 for f in flights_items if f.get('freeSeats', f.get('free_seats', 0)) > 0)

            recent_flights = _normalize_keys(recent_data.get('items', []))
            airports_map = _fetch_airports_map(self.request)
            recent_flights_enriched = _enrich_flights_with_airports(recent_flights, airports_map)

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
        search_form = FlightSearchForm(self.request.GET)

        items, total = [], 0

        if search_form.is_valid():
            stype = search_form.cleaned_data.get('search_type')
            query = search_form.cleaned_data.get('query', '').strip()
            try:
                if stype == 'number' and query:
                    # search_by_number возвращает список, используем его
                    items = FlightController.search_by_number(query.upper(), token) if hasattr(FlightController,
                                                                                               'search_by_number') else []
                    # Если метода нет, используем get_flight_with_passengers
                    if not items:
                        data = FlightController.get_flight_with_passengers(query.upper(), token)
                        if data.get('flight'):
                            items = [data['flight']]
                    total = len(items)
                elif stype == 'arrival' and query:
                    items = FlightController.search_by_arrival(query, token)
                    total = len(items)
                else:
                    data = FlightController.get_all_flights(page=page_num, size=10, access_token=token)
                    items = data.get('items', [])
                    total = data.get('total', 0)
            except Exception:
                pass
        else:
            data = FlightController.get_all_flights(page=page_num, size=10, access_token=token)
            items = data.get('items', [])
            total = data.get('total', 0)

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
        """Проверка существования рейса перед рендером"""
        token = request.session.get('access_token')
        flight_id = kwargs.get('pk')

        flight_data = FlightController.get_flight_by_id(flight_id, token)
        if not flight_data:
            messages.error(request, 'Рейс не найден')
            return redirect('app:flight_list')

        # Сохраняем данные в self для использования в get_context_data
        self._cached_flight_data = flight_data
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        """Подготовка контекста для шаблона"""
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))

        token = self.request.session.get('access_token')
        flight_id = kwargs.get('pk')

        # ✅ Используем кэшированные данные из get() или делаем новый запрос
        flight_data = getattr(self, '_cached_flight_data', None)
        if flight_data is None:
            flight_data = FlightController.get_flight_by_id(flight_id, token)
            if not flight_data:
                messages.error(self.request, 'Рейс не найден')
                # Возвращаем пустой контекст, редирект из get() сработает при следующем запросе
                return context

        # Получаем пассажиров по номеру рейса
        flight_number = flight_data.get('flightNumber')
        full_data = FlightController.get_flight_with_passengers(flight_number, token)
        flight_data = full_data.get('flight', flight_data)
        passengers_data = full_data.get('passengers', [])

        # Нормализация и обогащение
        airports_map = _fetch_airports_map(self.request)
        flight_normalized = _normalize_keys(flight_data)

        # ✅ Проверка: если нормализация вернула None, не передаём в enrich
        if flight_normalized is None:
            messages.error(self.request, 'Ошибка обработки данных рейса')
            return context

        flight_enriched = _enrich_flights_with_airports([flight_normalized], airports_map)[0]

        context.update({
            'flight': flight_enriched,
            'passengers': _normalize_keys(passengers_data)
        })

        return context


class FlightDeleteView(View):
    """Удаление рейса через API (POST запрос)"""

    def post(self, request, pk):
        token = request.session.get('access_token')

        # Вызываем метод удаления через контроллер
        success = FlightController.delete_flight(pk, token)

        if success:
            messages.success(request, 'Рейс успешно удалён')
        else:
            messages.error(request, 'Ошибка при удалении рейса (возможно, есть активные бронирования)')

        return redirect('app:flight_list')


# ==========================================
# 👥 ПАССАЖИРЫ
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


# ==========================================
# 🎫 БРОНИРОВАНИЯ
# ==========================================

class BookingCreateView(FormView):
    template_name = 'bookings/create.html'
    # form_class берется из urls или переопределяется, если нужно
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