from django.db import models
from django.core.validators import RegexValidator


class Passenger(models.Model):
    """Пассажир"""
    passport_validator = RegexValidator(
        regex=r'^\d{4}-\d{6}$',
        message="Номер паспорта должен быть в формате NNNN-NNNNNN"
    )

    passport_number = models.CharField(
        max_length=11,
        validators=[passport_validator],
        verbose_name="№ паспорта",
        unique=True,
        help_text="Формат: NNNN-NNNNNN"
    )
    passport_issued_by = models.CharField(
        max_length=255,
        verbose_name="Место выдачи"
    )
    passport_issue_date = models.DateField(verbose_name="Дата выдачи")

    full_name = models.CharField(max_length=255, verbose_name="ФИО")
    birth_date = models.DateField(verbose_name="Дата рождения")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Пассажир"
        verbose_name_plural = "Пассажиры"
        ordering = ['full_name']

    def __str__(self):
        return f"{self.full_name} ({self.passport_number})"