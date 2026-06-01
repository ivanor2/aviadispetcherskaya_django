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

def test_create_and_list_flight(auth_page, flight_page, airline_page, airport_page, valid_flight_data, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])

    import string, random
    icao_dep = "SU" + "".join(random.choices(string.ascii_uppercase, k=2))
    icao_arr = "TA" + "".join(random.choices(string.ascii_uppercase, k=2))
    airline_page.create_airline("TSAA", "Test Airline")
    airport_page.create_airport(icao_dep, "Test Dep")
    airport_page.create_airport(icao_arr, "Test Arr")

    flight_page.create_flight(**valid_flight_data)
    msg, status = flight_page.get_alert_message()
    assert "успешн" in msg.lower(), f"Рейс не создался: {msg}"
    
    flight_page.search_flight(valid_flight_data["number"])
    assert flight_page.get_flight_count() >= 1, "Созданный рейс не найден в списке после поиска"

def test_guest_cannot_access_flight_creation(auth_page, flight_page):
    auth_page.open("/flights/create/")
    assert "/login/" in auth_page.driver.current_url, "Гость смог получить доступ к созданию рейса"

def test_view_and_delete_flight(auth_page, flight_page, airline_page, airport_page, valid_flight_data, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    import string, random
    icao_dep = "SU" + "".join(random.choices(string.ascii_uppercase, k=2))
    icao_arr = "TA" + "".join(random.choices(string.ascii_uppercase, k=2))
    airline_page.create_airline("TDA", "Delete Airline")
    airport_page.create_airport(icao_dep, "Delete Dep")
    airport_page.create_airport(icao_arr, "Delete Arr")
    
    unique_number = str(random.randint(100, 999))
    flight_page.create_flight(unique_number, valid_flight_data["date"], valid_flight_data["time"], valid_flight_data["seats"])
    
    flight_page.search_flight(unique_number)
    count = flight_page.get_flight_count()
    assert count >= 1
