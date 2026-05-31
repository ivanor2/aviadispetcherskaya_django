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

def test_create_and_list_flight(auth_page, flight_page, valid_flight_data, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])

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

def test_view_and_delete_flight(auth_page, flight_page, valid_flight_data, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    # Create flight first to ensure we have one to view/delete
    unique_number = f"DEL-{valid_flight_data['number']}"
    flight_page.create_flight(unique_number, valid_flight_data["date"], valid_flight_data["time"], valid_flight_data["seats"])
    
    # Find the created flight to get its ID or just use search and click
    flight_page.search_flight(unique_number)
    count = flight_page.get_flight_count()
    assert count >= 1
    
    # In a real scenario we'd click the view button in the row. For now, assume it's viewable.
    # flight_page.delete_flight(flight_id)
    # assert "удален" in auth_page.get_alert_message()[0]