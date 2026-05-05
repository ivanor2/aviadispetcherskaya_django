from django.views import View
from django.views.generic import FormView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django import forms
from app.forms import BookingForm
from app.controllers import BookingController, FlightController
from app.utils import _get_token, _get_role_perms, _normalize_keys

class BookingCreateView(FormView):
    template_name = 'bookings/create.html'
    form_class = BookingForm
    success_url = reverse_lazy('app:flight_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(_get_role_perms(self.request))

        flight_id = self.kwargs.get('flight_id')
        token = _get_token(self.request)
        flight_data = FlightController.get_flight_by_id(flight_id, token)

        if flight_data:
            context['flight'] = _normalize_keys(flight_data)
        else:
            messages.error(self.request, 'Рейс не найден')

        form = self.get_form()
        context['passenger_choices'] = form.passenger_choices
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['access_token'] = _get_token(self.request)
        kwargs['current_flight_id'] = self.kwargs.get('flight_id')
        return kwargs

    def form_valid(self, form):
        token = _get_token(self.request)
        flight_id = self.kwargs.get('flight_id')

        passenger_ids_raw = self.request.POST.getlist('passenger_ids')
        passenger_ids = [int(pid) for pid in passenger_ids_raw if pid and pid.strip()]

        if not passenger_ids:
            form.add_error(None, 'Необходимо выбрать хотя бы одного пассажира')
            return self.form_invalid(form)

        connection_id = form.cleaned_data.get('connection_flight_id')

        payload = {
            'flightId': flight_id,
            'passengerIds': passenger_ids,
        }

        if connection_id:
            payload['connectionFlightIds'] = [int(connection_id)]

        success, data, msg = BookingController.create_booking(payload, token)

        if success:
            booking_code = data[0].get('bookingCode', 'N/A') if data else 'N/A'
            messages.success(self.request, f'Билеты оформлены! Код: {booking_code}')
            return redirect('app:flight_detail', pk=flight_id)

        messages.error(self.request, f'Ошибка: {msg}')
        return self.form_invalid(form)

class BookingConnectionView(FormView):
    template_name = 'bookings/add_connection.html'
    form_class = type('AddConnectionForm', (forms.Form,), {
        'booking_code': forms.CharField(label='Код бронирования', widget=forms.TextInput(attrs={'class': 'form-control'})),
        'flight_id': forms.IntegerField(label='ID рейса пересадки', widget=forms.NumberInput(attrs={'class': 'form-control'}))
    })
    success_url = reverse_lazy('app:flight_list')

    def form_valid(self, form):
        token = _get_token(self.request)
        success, data, msg = BookingController.add_connections(
            form.cleaned_data['booking_code'],
            [form.cleaned_data['flight_id']],
            token
        )
        if success:
            messages.success(self.request, msg)
            return redirect('app:flight_list')
        messages.error(self.request, f'Ошибка: {msg}')
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

class BookingFlightSelectView(View):
    def get(self, request):
        flight_id = request.GET.get('flight_id')
        if not flight_id:
            messages.error(request, 'Пожалуйста, выберите рейс из списка')
            return redirect('app:index')
        try:
            return redirect('app:booking_create', flight_id=int(flight_id))
        except ValueError:
            messages.error(request, 'Некорректный идентификатор рейса')
            return redirect('app:index')

class BookingDeleteView(View):
    def post(self, request, booking_id):
        if request.session.get('user_role') != 'admin':
            messages.error(request, 'Доступ запрещён. Требуются права администратора.')
            return redirect('app:flight_list')

        token = _get_token(request)
        flight_id = request.POST.get('flight_id')

        success, msg = BookingController.delete_booking(booking_id, token)

        if success:
            messages.success(request, msg)
        else:
            messages.error(request, msg)

        if flight_id:
            return redirect('app:flight_detail', pk=flight_id)
        return redirect('app:flight_list')