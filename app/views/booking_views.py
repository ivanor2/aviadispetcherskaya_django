import os
from datetime import datetime
from io import BytesIO

from django.http import HttpResponse
from django.template.loader import render_to_string
from django.views import View
from django.views.generic import FormView
from django.shortcuts import redirect, render
from django.contrib import messages
from django.urls import reverse_lazy
from django import forms
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa

from app.forms import BookingForm
from app.controllers import BookingController, FlightController, PassengerController
from app.utils import _get_token, _get_role_perms, _normalize_keys, _parse_datetime_safe, _parse_time, \
    _fetch_airlines_map, _fetch_airports_map
from django_app import settings


class BookingCreateView(FormView):
    template_name = 'bookings/create.html'
    form_class = BookingForm
    success_url = reverse_lazy('app:flight_list')

    def dispatch(self, request, *args, **kwargs):
        if request.session.get('user_role') == 'guest':
            messages.error(request, 'Доступ запрещён. Гости не могут продавать билеты.')
            return redirect('app:index')
        return super().dispatch(request, *args, **kwargs)

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

        # === СБОР МЕСТ ИЗ СТРОК ===
        seats_raw = self.request.POST.getlist('seats')
        seats_list = [s.strip() for s in seats_raw if s and s.strip()]

        # Если места указаны, их количество должно совпадать с количеством пассажиров
        if seats_list and len(seats_list) != len(passenger_ids):
            form.add_error(None,
                           f'Количество заполненных мест ({len(seats_list)}) должно совпадать с количеством пассажиров ({len(passenger_ids)})')
            return self.form_invalid(form)

        payload = {
            'flightId': flight_id,
            'passengerIds': passenger_ids,
            'baggageAllowed': form.cleaned_data.get('baggage_allowed', False),
            'paymentType': form.cleaned_data.get('payment_type', 'card'),
            'basePrice': float(form.cleaned_data.get('base_price', 0)),
            'tax': float(form.cleaned_data.get('tax', 0)),
            'additionalFees': float(form.cleaned_data.get('additional_fees', 0)),
            'classType': form.cleaned_data.get('class_type', 'economy')
        }

        # Передаем места в API только если они заполнены
        if seats_list:
            payload['seats'] = seats_list

        connection_id = form.cleaned_data.get('connection_flight_id')
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


class BookingTicketPdfView(View):
    def get(self, request, booking_id):
        token = _get_token(request)

        # === 1. БЕЗОПАСНЫЙ ПОИСК (избегаем 422 из-за size=500) ===
        booking_data = None
        page = 1
        max_pages = 5  # Проверяем первые 5 страниц (~250 записей)

        while page <= max_pages and not booking_data:
            # size=50 - безопасное значение по умолчанию для fastapi-pagination
            data = BookingController.get_all_bookings(page=page, size=50, access_token=token)
            for b in data.get('items', []):
                # Безопасное сравнение ID (API может вернуть строку "36" или число 36)
                b_id = b.get('id')
                if b_id is not None and int(b_id) == int(booking_id):
                    booking_data = b
                    break
            page += 1

        if not booking_data:
            return HttpResponse("❌ Бронирование не найдено или недоступно", status=404)

        booking = _normalize_keys(booking_data)

        # === 2. Получаем пассажира и рейс ===
        passenger_id = booking.get('passenger_id') or booking.get('passengerId')
        flight_id = booking.get('flight_id') or booking.get('flightId')

        passenger = PassengerController.get_passenger_by_id(passenger_id, token) if passenger_id else None
        flight = FlightController.get_flight_by_id(flight_id, token) if flight_id else None

        if passenger: passenger = _normalize_keys(passenger)
        if flight: flight = _normalize_keys(flight)

        if not flight:
            return HttpResponse("❌ Рейс для данного бронирования не найден", status=404)

        # === 3. Обогащаем данные (названия аэропортов, авиакомпаний) ===
        airlines_map = _fetch_airlines_map(request)
        airports_map = _fetch_airports_map(request)

        dep_icao = (flight.get('departure_airport_icao') or flight.get('departureAirportIcao', '')).strip().upper()
        arr_icao = (flight.get('arrival_airport_icao') or flight.get('arrivalAirportIcao', '')).strip().upper()
        airline_code = (flight.get('airline_code') or flight.get('airlineCode', '')).strip().upper()

        dep_name = airports_map.get(dep_icao, {}).get('name') or dep_icao or 'N/A'
        arr_name = airports_map.get(arr_icao, {}).get('name') or arr_icao or 'N/A'
        airline_name = airlines_map.get(airline_code, '') or airline_code or 'N/A'

        dep_date_obj = _parse_datetime_safe(flight.get('departure_date'))
        dep_date_str = dep_date_obj.strftime('%d.%m.%Y') if dep_date_obj else str(flight.get('departure_date', ''))[
                                                                                  :10] or 'N/A'

        dep_time_obj = _parse_time(flight.get('departure_time'))
        dep_time_str = dep_time_obj.strftime('%H:%M') if hasattr(dep_time_obj, 'strftime') else str(dep_time_obj)[
            :5] if dep_time_obj else 'N/A'

        passenger_name = passenger.get('full_name', 'N/A') if passenger else 'N/A'

        # ✅ ИЗВЛЕКАЕМ НОМЕР МЕСТА
        seat = booking.get('seat') or booking.get('seat_number', 'Автоназначение')
        if isinstance(seat, str) and seat.strip():
            seat = seat.strip().upper()
        else:
            seat = '—'

        # Расчет цены
        base_price = float(booking.get('base_price', 0))
        tax = float(booking.get('tax', 0))
        fees = float(booking.get('additional_fees', 0))
        final_price = booking.get('final_price') or booking.get('finalPrice') or (base_price + tax + fees)

        # === 4. Генерация PDF ===
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
                                topMargin=15 * mm, bottomMargin=15 * mm)

        font_path = os.path.join(settings.BASE_DIR, 'app', 'assets', 'fonts', 'DejaVuSans.ttf')
        base_font = 'Helvetica'
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVu', font_path))
            base_font = 'DejaVu'

        styles = getSampleStyleSheet()
        story = []

        title_style = ParagraphStyle('Title', parent=styles['Normal'], fontName=base_font, fontSize=14,
                                     alignment=TA_CENTER, spaceAfter=5 * mm)
        info_style = ParagraphStyle('Info', parent=styles['Normal'], fontName=base_font, fontSize=10, spaceAfter=2 * mm)

        story.append(Paragraph("ЭЛЕКТРОННЫЙ БИЛЕТ", title_style))
        story.append(Spacer(1, 5 * mm))

        story.append(Paragraph(f"<b>Пассажир:</b> {passenger_name.upper()}", info_style))
        story.append(Paragraph(f"<b>Рейс:</b> {flight.get('flight_number') or 'N/A'} | {airline_name}", info_style))
        story.append(Paragraph(f"<b>Маршрут:</b> {dep_name} → {arr_name}", info_style))
        story.append(Paragraph(f"<b>Дата/Время:</b> {dep_date_str} {dep_time_str}", info_style))
        story.append(Paragraph(f"<b>Класс:</b> {booking.get('class_type', 'Economy').upper()}", info_style))

        # ✅ НОВОЕ: Строка с местом в билете
        story.append(Paragraph(f"<b>Место / Seat:</b> {seat}", info_style))

        story.append(
            Paragraph(f"<b>Багаж:</b> {'Включен' if booking.get('baggage_allowed') else 'Не включен'}", info_style))
        story.append(Paragraph(f"<b>Код бронирования:</b> {booking.get('booking_code', 'N/A')}", info_style))

        story.append(Spacer(1, 5 * mm))
        story.append(Paragraph("<b>Расчет стоимости:</b>", info_style))

        price_table_data = [
            ['Базовая цена', f"{base_price:.2f} RUB"],
            ['Налоги', f"{tax:.2f} RUB"],
            ['Доп. сборы', f"{fees:.2f} RUB"],
            ['<b>ИТОГО</b>', f"<b>{final_price:.2f} RUB</b>"]
        ]

        t = Table(price_table_data, colWidths=[100 * mm, 50 * mm])
        t.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), base_font),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('LINEBELOW', (0, 0), (-1, 0), 1, colors.black),
            ('LINEBELOW', (0, -2), (-1, -2), 1, colors.black),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(t)

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="ticket_{booking.get("booking_code", "ticket")}.pdf"'
        return response