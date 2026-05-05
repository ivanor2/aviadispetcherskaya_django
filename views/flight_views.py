from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from app.forms import FlightSearchForm, FlightForm
from app.controllers import FlightController
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

        flight_data = getattr(self, '_cached_flight_data', None)
        token = self.request.session.get('access_token')
        flight_number = flight_data.get('flightNumber') or flight_data.get('flight_number', '')

        passengers_data = []
        try:
            if flight_number:
                full_data = FlightController.get_flight_with_passengers(flight_number, token)
                if isinstance(full_data, dict) and full_data.get('flight'):
                    flight_data = full_data['flight']
                passengers_data = full_data.get('passengers', [])
        except Exception as e:
            print(f"⚠️ Не удалось загрузить пассажиров для рейса {kwargs.get('pk')}: {e}")

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