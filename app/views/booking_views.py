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

        # === СБОР КОНКРЕТНЫХ МЕСТ ДЛЯ КАЖДОГО ПАССАЖИРА ===
        seats_raw = self.request.POST.getlist('seats')
        seats_list = [s.strip() for s in seats_raw[:len(passenger_ids)]]

        # Дозаполняем пустыми строками, если мест в POST пришло меньше, чем пассажиров
        while len(seats_list) < len(passenger_ids):
            seats_list.append("")

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

        if any(seats_list):
            payload['seats'] = seats_list

        connection_id = form.cleaned_data.get('connection_flight_id')
        if connection_id:
            payload['connectionFlightIds'] = [int(connection_id)]

        success, data, msg = BookingController.create_booking(payload, token)

        if success:
            booking_code = data[0].get('bookingCode', 'N/A') if data else 'N/A'
            messages.success(self.request, f'Билеты успешно оформлены! Номер брони: {booking_code}')
            return redirect('app:flight_detail', pk=flight_id)

        messages.error(self.request, f'Ошибка создания бронирования: {msg}')
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

        # === 1. БЕЗОПАСНЫЙ ПОИСК БРОНИРОВАНИЯ ===
        booking_data = None
        page = 1
        max_pages = 5

        while page <= max_pages and not booking_data:
            data = BookingController.get_all_bookings(page=page, size=50, access_token=token)
            for b in data.get('items', []):
                b_id = b.get('id')
                if b_id is not None and int(b_id) == int(booking_id):
                    booking_data = b
                    break
            page += 1

        if not booking_data:
            return HttpResponse("❌ Бронирование не найдено или недоступно", status=404)

        booking = _normalize_keys(booking_data)

        # === 2. ПОЛУЧАЕМ РЕЙС ===
        flight_id = booking.get('flight_id') or booking.get('flightId')
        flight = FlightController.get_flight_by_id(flight_id, token) if flight_id else None
        if flight: flight = _normalize_keys(flight)

        if not flight:
            return HttpResponse("❌ Рейс для данного бронирования не найден", status=404)

        # === 3. ОБОГАЩАЕМ ДАННЫЕ РЕЙСА ===
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

        # === 4. ОБРАБОТКА ДАННЫХ БРОНИ (ДЛЯ ВСЕХ ПАССАЖИРОВ) ===
        raw_p_ids = booking.get('passenger_ids') or booking.get('passengerIds')
        if raw_p_ids and isinstance(raw_p_ids, list):
            passenger_ids = raw_p_ids
        else:
            # Если массива нет, ищем одиночного пассажира
            single_p_id = booking.get('passenger_id') or booking.get('passengerId')
            passenger_ids = [single_p_id] if single_p_id else []

        # 2. Пытаемся найти массив мест
        raw_seats = booking.get('seats')
        if raw_seats and isinstance(raw_seats, list):
            seats = raw_seats
        else:
            # Если массива нет, ищем одиночное место
            single_seat = booking.get('seat') or booking.get('seat_number')
            seats = [single_seat] if single_seat else []

        # 3. Финансы


        # 4. Перевод класса обслуживания
        class_type_raw = booking.get('class_type') or booking.get('classType') or 'economy'
        class_map = {'economy': 'ЭКОНОМ', 'business': 'БИЗНЕС', 'first': 'ПЕРВЫЙ КЛАСС'}
        class_type_display = class_map.get(class_type_raw.lower(), class_type_raw.upper())
        baggage_status = 'Включен' if booking.get('baggage_allowed') or booking.get('baggageAllowed') else 'Не включен'

        flight_base_price = float(flight.get('base_price') or flight.get('basePrice') or 0) if flight else 0

        # 2. Умножаем на коэффициент выбранного класса
        if class_type_raw == 'business':
            base_price = flight_base_price * 2.0
        elif class_type_raw == 'first':
            base_price = flight_base_price * 3.0
        else:
            base_price = flight_base_price

        # 3. Считаем налог (строго 22% от полученной базовой цены)
        tax = base_price * 0.22

        # 4. Доп. сборы (багаж и ручные сборы) оставляем из брони, так как они индивидуальны для каждого билета
        fees = float(booking.get('additional_fees') or booking.get('additionalFees') or 0)

        # 5. Итоговая цена - всегда считаем сами
        final_price = base_price + tax + fees

        # === 5. ПОДГОТОВКА ДОКУМЕНТА REPORTLAB ===
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

        if not passenger_ids:
            story.append(Paragraph("Нет данных о пассажирах", title_style))
        else:
            # === ГЕНЕРАЦИЯ БИЛЕТОВ (ЦИКЛ ПО ПАССАЖИРАМ) ===
            for idx, p_id in enumerate(passenger_ids):
                # Если это второй или последующий пассажир — добавляем разрыв страницы
                if idx > 0:
                    story.append(PageBreak())

                # Получаем данные конкретного пассажира
                passenger = PassengerController.get_passenger_by_id(p_id, token)
                if passenger: passenger = _normalize_keys(passenger)

                passenger_name = passenger.get('full_name') or passenger.get(
                    'fullName') or 'Неизвестный' if passenger else 'N/A'
                passport = passenger.get('passport_number') or passenger.get(
                    'passportNumber') or 'N/A' if passenger else 'N/A'

                # Получаем место для текущего пассажира по его индексу в массиве
                seat = seats[idx] if idx < len(seats) and seats[idx] else 'Автоназначение'
                if isinstance(seat, str) and seat.strip():
                    seat = seat.strip().upper()

                # Рисуем билет
                story.append(Paragraph("ЭЛЕКТРОННЫЙ ПОСАДОЧНЫЙ ТАЛОН", title_style))
                story.append(Spacer(1, 5 * mm))

                story.append(Paragraph(f"<b>Пассажир:</b> {passenger_name.upper()} (Паспорт: {passport})", info_style))
                story.append(
                    Paragraph(f"<b>Рейс:</b> {flight.get('flight_number') or 'N/A'} | {airline_name}", info_style))
                story.append(Paragraph(f"<b>Маршрут:</b> {dep_name} → {arr_name}", info_style))
                story.append(Paragraph(f"<b>Дата/Время:</b> {dep_date_str} {dep_time_str}", info_style))
                story.append(Paragraph(f"<b>Класс обслуживания:</b> {class_type_display}", info_style))

                # НОВОЕ: Конкретное место пассажира
                story.append(Paragraph(f"<b>Место / Seat:</b> <font size=12><b>{seat}</b></font>", info_style))

                story.append(Paragraph(f"<b>Багаж:</b> {baggage_status}", info_style))
                story.append(Paragraph(
                    f"<b>Код бронирования:</b> {booking.get('booking_code') or booking.get('bookingCode') or 'N/A'}",
                    info_style))

                story.append(Spacer(1, 5 * mm))

                # Таблица цен (указываем, что это цена за ВЕСЬ заказ)
                story.append(Paragraph("<b>Детализация стоимости (за весь заказ):</b>", info_style))

                price_table_data = [
                    ['Базовый тариф', f"{base_price:.2f} RUB"],
                    ['Налоги (НДС 22%)', f"{tax:.2f} RUB"],
                    ['Доп. сборы и багаж', f"{fees:.2f} RUB"],
                    ['<b>ИТОГО К ОПЛАТЕ</b>', f"<b>{final_price:.2f} RUB</b>"]
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
        booking_code = booking.get("booking_code") or booking.get("bookingCode") or "ticket"
        response['Content-Disposition'] = f'attachment; filename="ticket_{booking_code}.pdf"'
        return response