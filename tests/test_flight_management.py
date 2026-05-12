import pytest
from datetime import datetime, timedelta

@pytest.fixture
def valid_flight_data():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "number": "123",
        "date": tomorrow,
        "time": "14:30",
        "seats": 150
    }

def test_create_and_list_flight(auth_page, flight_page, valid_flight_data):
    # Вход в систему
    auth_page.login("test_dispatcher", "Dispatcher123!") # Предполагаем, что тестовый юзер уже создан или создается в CI

    # Создание рейса
    flight_page.create_flight(**valid_flight_data)
    msg, status = flight_page.get_alert_message()
    assert "успешн" in msg.lower(), f"Рейс не создался: {msg}"

    # Поиск созданного рейса
    flight_page.search_flight(valid_flight_data["number"])
    assert flight_page.get_flight_count() >= 1, "Созданный рейс не найден в списке после поиска"

def test_guest_cannot_access_flight_creation(auth_page, flight_page):
    # Гость по умолчанию перенаправляется на логин через middleware
    auth_page.open("/flights/create/")
    assert "/login/" in auth_page.driver.current_url, "Гость смог получить доступ к созданию рейса"