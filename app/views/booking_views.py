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

        connection_id = form.cleaned_data.get('connection_flight_id')

        payload = {
            'flightId': flight_id,
            'passengerIds': passenger_ids,
            'baggageAllowed': form.cleaned_data.get('baggage_allowed', False),
            'paymentType': form.cleaned_data.get('payment_type', 'card'),
            'basePrice': float(form.cleaned_data.get('base_price', 0)),
            'tax': float(form.cleaned_data.get('tax', 0)),
            'additionalFees': float(form.cleaned_data.get('additional_fees', 0))
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


class BookingTicketPdfView(View):
    def get(self, request, booking_id):
        token = _get_token(request)

        # === 1. Получаем бронирование ===
        all_bookings = BookingController.get_all_bookings(page=1, size=100, access_token=token)
        booking_data = None
        for b in all_bookings.get('items', []):
            if b.get('id') == booking_id:
                booking_data = b
                break
        if not booking_data:
            return HttpResponse("Бронирование не найдено", status=404)
        booking = _normalize_keys(booking_data)

        # === 2. Получаем пассажира и рейс ===
        passenger = PassengerController.get_passenger_by_id(booking['passenger_id'], token)
        flight = FlightController.get_flight_by_id(booking['flight_id'], token)

        if passenger: passenger = _normalize_keys(passenger)
        if flight: flight = _normalize_keys(flight)

        # === 3. Подготавливаем данные (ОБОГАЩЕНИЕ: ИМЕНА АЭРОПОРТОВ И АВИАКОМПАНИЙ) ===
        airlines_map = _fetch_airlines_map(request)
        airports_map = _fetch_airports_map(request)

        dep_icao = (flight.get('departure_airport_icao') or flight.get('departureAirportIcao', '')).strip().upper()
        arr_icao = (flight.get('arrival_airport_icao') or flight.get('arrivalAirportIcao', '')).strip().upper()
        airline_code = (flight.get('airline_code') or flight.get('airlineCode', '')).strip().upper()

        dep_name = airports_map.get(dep_icao, {}).get('name') or dep_icao or 'N/A'
        arr_name = airports_map.get(arr_icao, {}).get('name') or arr_icao or 'N/A'
        airline_name = airlines_map.get(airline_code, '') or airline_code or 'N/A'

        # Дата и время отправления
        dep_date_obj = _parse_datetime_safe(flight.get('departure_date'))
        dep_date_str = dep_date_obj.strftime('%d.%m.%Y') if dep_date_obj else (
                    str(flight.get('departure_date', ''))[:10] or 'N/A')

        dep_time_obj = _parse_time(flight.get('departure_time'))
        dep_time_str = dep_time_obj.strftime('%H:%M') if isinstance(dep_time_obj, datetime) or hasattr(dep_time_obj,
                                                                                                       'strftime') else str(
            dep_time_obj)[:5] if dep_time_obj else 'N/A'

        passenger_name = passenger.get('full_name', 'N/A') if passenger else 'N/A'
        issue_date_obj = _parse_datetime_safe(booking.get('created_at'))
        issue_date_str = issue_date_obj.strftime('%d.%m.%Y') if issue_date_obj else (
                    str(booking.get('created_at', ''))[:10] or 'N/A')

        # Финальная цена (фолбэк на расчет, если поле не пришло)
        final_price = booking.get('final_price') or booking.get('finalPrice')
        if final_price is None:
            final_price = float(
                booking.get('base_price', 0) + booking.get('tax', 0) + booking.get('additional_fees', 0))

        # === 4. Создаём PDF ===
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm, topMargin=15 * mm,
                                bottomMargin=15 * mm)

        font_path = os.path.join(settings.BASE_DIR, 'app', 'assets', 'fonts', 'DejaVuSans.ttf')
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('DejaVu', font_path))
            base_font = 'DejaVu'
        else:
            base_font = 'Helvetica'

        styles = getSampleStyleSheet()
        story = []

        # Стили
        title_style = ParagraphStyle('TicketTitle', parent=styles['Normal'], fontName=base_font, fontSize=11,
                                     alignment=TA_CENTER, spaceAfter=2 * mm)
        subtitle_style = ParagraphStyle('TicketSubtitle', parent=styles['Normal'], fontName=base_font, fontSize=9,
                                        alignment=TA_CENTER, spaceAfter=5 * mm)
        info_style = ParagraphStyle('InfoLine', parent=styles['Normal'], fontName=base_font, fontSize=9,
                                    spaceAfter=2 * mm)
        route_style = ParagraphStyle('RouteInfo', parent=styles['Normal'], fontName=base_font, fontSize=9,
                                     spaceAfter=2 * mm)

        story.append(Paragraph("ЭЛЕКТРОННЫЙ БИЛЕТ (МАРШРУТ/КВИТАНЦИЯ)", title_style))
        story.append(Paragraph("ELECTRONIC TICKET (ITINERARY/RECEIPT)", subtitle_style))

        # ✅ НОВОЕ: Поле авиакомпании
        story.append(Paragraph(f"АВИАКОМПАНИЯ / AIRLINE: {airline_name}", info_style))
        # ✅ ИСПРАВЛЕНО: Дата + Время отправления в одной строке
        story.append(Paragraph(f"ДАТА И ВРЕМЯ / DATE & TIME: {dep_date_str} {dep_time_str}", info_style))
        story.append(Paragraph(f"ФАМИЛИЯ/NAME: {passenger_name.upper()}", info_style))
        story.append(Spacer(1, 3 * mm))

        # ✅ ИСПРАВЛЕНО: Маршрут теперь с полными названиями
        story.append(Paragraph(f"ОТПР/HASH/ORIG/DESTN: {dep_name} ✈️ {arr_name}", route_style))
        story.append(Paragraph(f"ВЫДАН ОТ/ISSUED BY: {issue_date_str}", route_style))
        story.append(Spacer(1, 3 * mm))

        ticket_number = f"{booking.get('id', 'N/A')}-001"
        story.append(Paragraph(f"НОМЕР БИЛЕТА/TICKET NUMBER: {ticket_number}", info_style))
        story.append(Paragraph("ДОПОЛНИТЕЛЬНЫЕ БИЛЕТЫ: ---", info_style))
        story.append(Paragraph(f"ДАННЫЕ БРОН/BOOKING REF: {booking.get('booking_code', 'N/A')}", info_style))
        story.append(Spacer(1, 5 * mm))

        story.append(Paragraph("ИНФОРМАЦИЯ О РЕЙСЕ:",
                               ParagraphStyle('FlightInfo', parent=styles['Normal'], fontName=base_font, fontSize=9,
                                              spaceAfter=2 * mm)))

        flight_data = [
            ['ОТ/ДО FROM/TO:', f"{dep_name} → {arr_name}"],
            ['РЕЙС FLIGHT:', flight.get('flight_number') or flight.get('flightNumber', 'N/A')],
            ['КЛ CLASS:', 'Y (Economy)'],
            ['ДАТА DATE:', dep_date_str],
            ['ВРЕМЯ DEP TIME:', dep_time_str],
            ['СТАТУС STATUS:', 'OK'],
            ['БАГАЖ BAG:', 'Да' if booking.get('baggage_allowed') else 'Нет'],
        ]

        flight_table = Table(flight_data, colWidths=[40 * mm, 80 * mm])
        flight_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), base_font),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 3),
        ]))
        story.append(flight_table)
        story.append(Spacer(1, 5 * mm))

        story.append(Paragraph("ПЕРЕДАТ. НАДПИСИ/ОГРАНИЧ./ENDORSEMENTS/RESTRICTIONS: ", info_style))
        story.append(Paragraph("NON-REFUNDABLE / НЕ ВОЗВРАТНЫЙ",
                               ParagraphStyle('Endorsement', parent=styles['Normal'], fontName=base_font, fontSize=8,
                                              spaceAfter=3 * mm)))

        payment_type = booking.get('payment_type', 'N/A').upper()
        story.append(Paragraph(f"ФОРМА ОПЛАТЫ/FORM OF PAYMENT: {payment_type}", info_style))
        story.append(Spacer(1, 3 * mm))

        story.append(Paragraph("РАСЧЕТ ТАРИФА/FARE CALCULATION: ", info_style))
        price_data = [
            ['ТАРИФ/FARE', f"{float(booking.get('base_price', 0)):.2f} RUB"],
            ['СБОР/TAX/FEE/CHARGE', f"{float(booking.get('tax', 0)):.2f} RUB"],
            ['ДОП. СБОРЫ/ADDITIONAL FEES', f"{float(booking.get('additional_fees', 0)):.2f} RUB"],
            ['', ''],
            ['ИТОГО/TOTAL', f"{float(final_price):.2f} RUB"],
        ]
        price_table = Table(price_data, colWidths=[80 * mm, 40 * mm])
        price_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), base_font),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LINEBELOW', (0, 0), (1, 0), 0.5, colors.black),
            ('LINEBELOW', (0, 1), (1, 1), 0.5, colors.black),
            ('LINEBELOW', (0, 2), (1, 2), 0.5, colors.black),
            ('LINEABOVE', (0, 4), (1, 4), 1, colors.black),
            ('BACKGROUND', (0, 4), (1, 4), colors.lightgrey),
            ('PADDING', (0, 0), (-1, -1), 4),
        ]))
        story.append(price_table)

        story.append(Spacer(1, 10 * mm))

        footer_style = ParagraphStyle('Footer', parent=styles['Normal'], fontName=base_font, fontSize=7,
                                      alignment=TA_CENTER, textColor=colors.grey)
        story.append(Paragraph("Данный документ является подтверждением бронирования.", footer_style))
        story.append(Paragraph(f"Сгенерировано: {datetime.now().strftime('%d.%m.%Y %H:%M')}", footer_style))

        doc.build(story)
        buffer.seek(0)

        response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
        filename = f"ticket_{booking.get('booking_code', 'ticket')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response