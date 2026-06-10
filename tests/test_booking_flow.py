import random
import pytest
from faker import Faker

faker = Faker("en_US")


def test_booking_flow(auth_page, flight_page, booking_page, passenger_page, airline_page, airport_page,
                      test_credentials, random_prefix):
    """Полный сценарий бронирования: создание данных → поиск рейса → оформление билета.

    Создаёт авиакомпанию, два аэропорта, рейс и пассажира, затем выполняет
    бронирование через UI и проверяет успешное завершение.
    """
    auth_page.login(test_credentials[0], test_credentials[1])

    unique_suffix = str(random.randint(100, 999))

    icao_dep = f"{random_prefix}{faker.lexify('??').upper()}"
    icao_arr = f"{random_prefix}{faker.lexify('??').upper()}"
    while icao_dep == icao_arr:
        icao_arr = f"{random_prefix}{faker.lexify('??').upper()}"

    airline_code = faker.lexify("???").upper()

    airline_page.create_airline(airline_code, "Booking Airline")
    airport_page.create_airport(icao_dep, "Dep Airport")
    airport_page.create_airport(icao_arr, "Arr Airport")

    flight_num = str(random.randint(100, 999))
    flight_page.create_flight(flight_num, "2026-12-01", "10:00", 100, airline_code=airline_code)

    passport = f"{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"
    passenger_name = f"Ivan {unique_suffix}"
    passenger_page.create_passenger(passenger_name, passport, "FMS", "2020-01-01", "1990-01-01")

    flight_page.search_flight(f"{airline_code}-{flight_num}")
    flight_page.click_book_button(flight_num)

    booking_page.create_booking(unique_suffix)

    msg, status = booking_page.get_alert_message()
    assert "успешн" in msg.lower() or status == "success", f"Бронирование не удалось создать: {msg}"