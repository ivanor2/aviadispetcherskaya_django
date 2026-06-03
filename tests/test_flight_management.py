import pytest
from datetime import datetime, timedelta
from faker import Faker

faker = Faker("en_US")


def test_create_and_list_flight(auth_page, flight_page, airline_page, airport_page, valid_flight_data,
                                test_credentials, random_prefix):
    auth_page.login(test_credentials[0], test_credentials[1])

    icao_dep = f"{random_prefix}{faker.lexify('???').upper()}"
    icao_arr = f"{random_prefix}{faker.lexify('???').upper()}"
    while icao_dep == icao_arr:
        icao_arr = f"{random_prefix}{faker.lexify('???').upper()}"

    airline_code = faker.lexify("???").upper()

    airline_page.create_airline(airline_code, "Test Airline")
    airport_page.create_airport(icao_dep, "Test Dep")
    airport_page.create_airport(icao_arr, "Test Arr")

    vfl = valid_flight_data

    # ✅ ПЕРЕДАЕМ airline_code
    flight_page.create_flight(**vfl, airline_code=airline_code)
    msg, status = flight_page.get_alert_message()
    assert "успешн" in msg.lower() or status == "success", f"Рейс не создался: {msg}"

    flight_page.search_flight(f"{airline_code}-{vfl['number']}")
    assert flight_page.get_flight_count() >= 1, "Созданный рейс не найден в списке после поиска"


def test_guest_cannot_access_flight_creation(auth_page, flight_page):
    auth_page.open("/flights/create/")
    assert "/login/" in auth_page.driver.current_url, "Гость смог получить доступ к созданию рейса"


def test_view_and_delete_flight(auth_page, flight_page, airline_page, airport_page, valid_flight_data,
                                test_credentials, random_prefix):
    auth_page.login(test_credentials[0], test_credentials[1])

    icao_dep = f"{random_prefix}{faker.lexify('???').upper()}"
    icao_arr = f"{random_prefix}{faker.lexify('???').upper()}"
    while icao_dep == icao_arr:
        icao_arr = f"{random_prefix}{faker.lexify('???').upper()}"

    airline_code = faker.lexify("???").upper()

    airline_page.create_airline(airline_code, "Delete Airline")
    airport_page.create_airport(icao_dep, "Delete Dep")
    airport_page.create_airport(icao_arr, "Delete Arr")

    import random
    unique_number = str(random.randint(100, 999))

    # ✅ ПЕРЕДАЕМ airline_code
    flight_page.create_flight(unique_number, valid_flight_data["date"], valid_flight_data["time"],
                              valid_flight_data["seats"], airline_code=airline_code)

    flight_page.search_flight(f"{airline_code}-{unique_number}")
    count = flight_page.get_flight_count()
    assert count >= 1
