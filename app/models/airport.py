from django.db import models


class Airport(models.Model):
    """Аэропорт с ICAO-индексом"""
    icao_code = models.CharField(
        max_length=4,
        unique=True,
        verbose_name="ICAO код",
        help_text="4 буквы латиницы, например: UUEE"
    )
    name = models.CharField(max_length=255, verbose_name="Название аэропорта")
    country = models.CharField(max_length=100, verbose_name="Страна")
    city = models.CharField(max_length=100, verbose_name="Город")

    class Meta:
        verbose_name = "Аэропорт"
        verbose_name_plural = "Аэропорты"
        ordering = ['name']

    def __str__(self):
        return f"{self.icao_code} - {self.name} ({self.city})"