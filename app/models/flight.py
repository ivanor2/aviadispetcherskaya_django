from django.db import models
from django.core.validators import RegexValidator
from .airport import Airport


class Flight(models.Model):
    """Авиарейс"""
    flight_number_validator = RegexValidator(
        regex=r'^[A-Z]{3}-\d{3}$',
        message="Номер рейса должен быть в формате AAA-NNN (например, SVO-123)"
    )

    flight_number = models.CharField(
        max_length=10,
        validators=[flight_number_validator],
        verbose_name="№ авиарейса",
        unique=True,
        help_text="Формат: AAA-NNN, где AAA - код авиакомпании, NNN - номер"
    )
    airline_name = models.CharField(max_length=255, verbose_name="Авиакомпания")

    departure_airport = models.ForeignKey(
        Airport,
        on_delete=models.PROTECT,
        related_name='departures',
        verbose_name="Аэропорт отправления"
    )
    arrival_airport = models.ForeignKey(
        Airport,
        on_delete=models.PROTECT,
        related_name='arrivals',
        verbose_name="Аэропорт прибытия"
    )

    departure_date = models.DateField(verbose_name="Дата отправления")
    departure_time = models.TimeField(verbose_name="Время отправления")

    total_seats = models.PositiveIntegerField(verbose_name="Всего мест")
    free_seats = models.PositiveIntegerField(verbose_name="Свободных мест")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Авиарейс"
        verbose_name_plural = "Авиарейсы"
        ordering = ['departure_date', 'departure_time']

    def __str__(self):
        return f"{self.flight_number} {self.departure_airport} → {self.arrival_airport}"

    def has_free_seats(self):
        return self.free_seats > 0

    def save(self, *args, **kwargs):
        """Авто-синхронизация free_seats при создании"""
        if not self.pk and self.free_seats is None:
            self.free_seats = self.total_seats
        super().save(*args, **kwargs)