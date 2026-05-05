import requests
from django.conf import settings
from django.views import View
from django.views.generic import TemplateView, FormView
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy
from app.forms import PassengerSearchForm, PassengerForm
from app.controllers import PassengerController, BookingController, FlightController
from app.utils import (
    _normalize_keys, _get_token, _get_role_perms,
    _parse_datetime_safe
)

class PassengerListView(TemplateView):
    template_name = 'passengers/list.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        token = _get_token(self.request)

        page_num = int(self.request.GET.get('page', 1)) if str(self.request.GET.get('page', 1)).isdigit() else 1
        search_type = self.request.GET.get('search_type', 'passport')
        query = self.request.GET.get('query', '').strip()

        items, total, pages = [], 0, 1

        try:
            if query:
                items = PassengerController.search_by_passport(query, token) if search_type == 'passport' else PassengerController.search_by_name(query, token)
                total = len(items)
                pages = max(1, (total + 9) // 10)
                start = (page_num - 1) * 10
                items = items[start:start + 10]
            else:
                data = PassengerController.get_all_passengers(page=page_num, size=10, access_token=token)
                items = data.get('items', [])
                total = data.get('total', 0)
                pages = data.get('pages', 1)
        except Exception:
            pass

        passengers = _normalize_keys(items)
        for p in passengers:
            p['birth_date'] = _parse_datetime_safe(p.get('birth_date'))
            p['passport_issue_date'] = _parse_datetime_safe(p.get('passport_issue_date'))
            passport = p.get('passport_number') or p.get('passportNumber')
            if passport:
                p['bookings_count'] = len(BookingController.get_bookings_by_passport(passport, token))
            else:
                p['bookings_count'] = 0

        page_obj = {
            'object_list': passengers,
            'number': page_num,
            'has_previous': page_num > 1,
            'has_next': page_num < pages,
            'paginator': {'num_pages': pages}
        }

        context.update({
            'passengers': page_obj['object_list'],
            'page_obj': page_obj,
            'is_paginated': total > 10,
            'search_form': {'search_type': search_type, 'query': query}
        })
        return context

class PassengerCreateView(FormView):
    template_name = 'passengers/create.html'
    form_class = PassengerForm
    success_url = reverse_lazy('app:passenger_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        return context

    def form_valid(self, form):
        token = _get_token(self.request)
        payload = {
            'passportNumber': form.cleaned_data['passport_number'],
            'passportIssuedBy': form.cleaned_data['passport_issued_by'],
            'passportIssueDate': form.cleaned_data['passport_issue_date'].isoformat(),
            'fullName': form.cleaned_data['full_name'],
            'birthDate': form.cleaned_data['birth_date'].isoformat()
        }
        success, data, msg = PassengerController.create_passenger(payload, token)
        if success:
            messages.success(self.request, msg)
            return super().form_valid(form)
        messages.error(self.request, msg)
        return self.form_invalid(form)


class PassengerDetailView(TemplateView):
    template_name = 'passengers/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))
        token = _get_token(self.request)
        pk = kwargs.get('pk')

        headers = {'Authorization': f'Bearer {token}'} if token else {}
        try:
            resp = requests.get(f"{settings.API_BASE_URL}/passengers/{pk}", headers=headers, timeout=5)
            if resp.status_code != 200:
                messages.error(self.request, 'Пассажир не найден')
                return redirect('app:passenger_list')
            p_data = resp.json()
        except Exception:
            messages.error(self.request, 'Ошибка подключения к API')
            return redirect('app:passenger_list')

        p = _normalize_keys(p_data)
        p['birth_date'] = _parse_datetime_safe(p.get('birth_date'))
        p['passport_issue_date'] = _parse_datetime_safe(p.get('passport_issue_date'))

        passport = p.get('passport_number')
        raw_bookings = BookingController.get_bookings_by_passport(passport, token) if passport else []

        enriched_bookings = []
        for b in raw_bookings:
            b_norm = _normalize_keys(b)
            b_norm['created_at'] = _parse_datetime_safe(b_norm.get('created_at') or b_norm.get('createdAt'))
            flight_id = b_norm.get('flight_id')
            if flight_id:
                flight_info = FlightController.get_flight_by_id(flight_id, token)
                if flight_info:
                    f_norm = _normalize_keys(flight_info)
                    b_norm['flight_number'] = f_norm.get('flight_number')
                    b_norm['departure_icao'] = f_norm.get('departure_airport_icao')
                    b_norm['arrival_icao'] = f_norm.get('arrival_airport_icao')
            enriched_bookings.append(b_norm)

        context.update({
            'passenger': p,
            'bookings': enriched_bookings,
            'bookings_count': len(enriched_bookings)
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
            items = PassengerController.search_by_passport(query, token) if stype == 'passport' else PassengerController.search_by_name(query, token)
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


class PassengerDeleteView(View):
    def post(self, request, pk):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён. Требуются права администратора.')
            return redirect('app:passenger_list')

        token = _get_token(request)
        success, msg = PassengerController.delete_passenger(pk, token)

        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)
        return redirect('app:passenger_list')