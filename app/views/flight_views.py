from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from app.forms import FlightSearchForm, FlightForm
from app.controllers import FlightController, PassengerController, BookingController
from app.utils import (
    _normalize_keys, _get_token, _get_role_perms,
    _fetch_airlines_map, _fetch_airports_map, _enrich_flights_data,
    _parse_datetime_safe, _parse_time
)

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

        normalized_items = _normalize_keys(items)
        airlines_map = _fetch_airlines_map(self.request)
        airports_map = _fetch_airports_map(self.request)
        enriched_items = _enrich_flights_data(normalized_items, airlines_map, airports_map)

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
            'arrivalTime': str(form.cleaned_data['arrival_time']),
            'totalSeats': form.cleaned_data['total_seats'],
            'freeSeats': form.cleaned_data['total_seats'],
            'basePrice': form.cleaned_data['base_price'],
            'baggagePrice': form.cleaned_data['baggage_price']
        }
        print("!!! ФОРМА ВАЛИДНА, СОБИРАЕМ ДАННЫЕ !!!")
        success, data, message = FlightController.create_flight(payload, _get_token(self.request))
        print(f"!!! ОТВЕТ ОТ API: success={success}, message={message} !!!")
        if success:
            messages.success(self.request, message)
            return super().form_valid(form)

        messages.error(self.request, message)
        return self.form_invalid(form)

        def form_invalid(self, form):
            print("!!! ОШИБКА ВАЛИДАЦИИ ФОРМЫ DJANGO !!!", form.errors)  # <-- и это
            return super().form_invalid(form)


class FlightDetailView(TemplateView):
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

        # 1. Получаем данные рейса
        flight_data = getattr(self, '_cached_flight_data', None)  # Если кэшировали
        if not flight_data:
            flight_id = self.kwargs.get('pk')
            flight_data = FlightController.get_flight_by_id(flight_id, token)

        if not flight_data:
            messages.error(self.request, 'Рейс не найден')
            return context

        flight_norm = _normalize_keys(flight_data)
        airlines_map = _fetch_airlines_map(self.request)
        airports_map = _fetch_airports_map(self.request)
        enriched_flights = _enrich_flights_data([flight_norm], airlines_map, airports_map)
        context['flight'] = enriched_flights[0] if enriched_flights else flight_norm


        flight_id = flight_data.get('id')
        if flight_id:
            bookings_data = BookingController.get_bookings_by_flight(flight_id, token)
            enriched_bookings = []
            for b in _normalize_keys(bookings_data):
                if 'passenger' not in b and 'passenger_id' in b:
                    p = PassengerController.get_passenger_by_id(b['passenger_id'], token)
                    if p:
                        p_norm = _normalize_keys(p)
                        b['passenger'] = p_norm

                # Парсим даты
                b['booked_at'] = _parse_datetime_safe(b.get('booked_at') or b.get('createdAt'))
                b['final_price'] = float(b.get('base_price', 0) + b.get('tax', 0) + b.get('additional_fees', 0))
                enriched_bookings.append(b)

            context['passengers'] = enriched_bookings
        else:
            context['passengers'] = []

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

class FlightDeleteAllView(View):
    def post(self, request):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён. Требуются права администратора.')
            return redirect('app:flight_list')

        token = request.session.get('access_token')
        success, message = FlightController.delete_all_flights(token)

        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)

        return redirect('app:flight_list')