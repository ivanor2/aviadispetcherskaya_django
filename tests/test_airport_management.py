import pytest
from faker import Faker

faker = Faker("en_US")


def test_create_airport(auth_page, airport_page, test_credentials, random_prefix):
    auth_page.login(test_credentials[0], test_credentials[1])

    icao = f"{random_prefix}{faker.lexify('???').upper()}"
    name = f"Airport {icao}"

    airport_page.create_airport(icao, name)

    # Если редирект прошел успешно, пытаемся отредактировать
    if "/airports/" in auth_page.driver.current_url:
        airport_page.edit_airport(icao, f"{name} New")
        msg, status = auth_page.get_alert_message()
        assert "успешн" in msg.lower() or status == "success", f"Не удалось отредактировать: {msg}"
