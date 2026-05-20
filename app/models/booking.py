from django.db import models
from .flight import Flight
from .passenger import Passenger
import secrets
import string

class Booking(models.Model):
    """Бронирование билета"""
    booking_code = models.CharField(
        max_length=10,
        unique=True,
        verbose_name="Код бронирования",
        editable=False,
        help_text="Уникальный код из 6 символов (буквы+цифры)"
    )
    flight = models.ForeignKey(
        Flight,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Авиарейс"
    )
    passenger = models.ForeignKey(
        Passenger,
        on_delete=models.CASCADE,
        related_name='bookings',
        verbose_name="Пассажир"
    )

    booked_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата бронирования")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    # === НОВЫЕ ПОЛЯ ИЗ API ===
    baggage_allowed = models.BooleanField(default=False, verbose_name="Багаж включен")
    payment_type = models.CharField(max_length=20, default="card", verbose_name="Тип оплаты")
    base_price = models.FloatField(default=0.0, verbose_name="Базовая цена")
    tax = models.FloatField(default=0.0, verbose_name="Налог")
    additional_fees = models.FloatField(default=0.0, verbose_name="Доп. сборы")
    class_type = models.CharField(max_length=20, default="economy", verbose_name="Класс обслуживания")

    class Meta:
        verbose_name = "Бронирование"
        verbose_name_plural = "Бронирования"
        ordering = ['-booked_at']

    def __str__(self):
        return f"{self.booking_code} - {self.passenger.full_name}"

    @property
    def final_price(self):
        """Вычисляет итоговую цену"""
        return self.base_price + self.tax + self.additional_fees

    def save(self, *args, **kwargs):
        """Генерация уникального кода бронирования"""
        if not self.booking_code:
            chars = string.ascii_uppercase + string.digits
            while True:
                code = ''.join(secrets.choice(chars) for _ in range(6))
                if not Booking.objects.filter(booking_code=code).exists():
                    self.booking_code = code
                    break
        super().save(*args, **kwargs)