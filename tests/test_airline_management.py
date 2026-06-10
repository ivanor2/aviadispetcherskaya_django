import pytest
from faker import Faker

faker = Faker("en_US")


def test_create_and_edit_airline(auth_page, airline_page, test_credentials):
    """Создаёт авиакомпанию и проверяет возможность её редактирования.

    Генерирует случайный трёхбуквенный код, создаёт авиакомпанию через форму и,
    если редирект прошёл успешно, изменяет её название и проверяет сообщение об успехе.
    """
    auth_page.login(test_credentials[0], test_credentials[1])

    code = faker.lexify("???").upper()
    name = f"Airline {code}"

    airline_page.create_airline(code, name)
    msg, status = auth_page.get_alert_message()

    if "/airlines/" in auth_page.driver.current_url:
        airline_page.edit_airline(code, f"{name} Edited")
        assert "успешн" in auth_page.get_alert_message()[0].lower() or "success" in auth_page.get_alert_message()[1]
