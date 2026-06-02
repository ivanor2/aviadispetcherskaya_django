import random

import pytest
from faker import Faker

faker = Faker("en_US")

def test_booking_flow(auth_page, flight_page, booking_page, passenger_page, airline_page, airport_page,
                      test_credentials, random_prefix):
    auth_page.login(test_credentials[0], test_credentials[1])

    unique_suffix = str(random.randint(100, 999))


    icao_dep = f"{random_prefix}{faker.lexify('??').upper()}"
    icao_arr = f"{random_prefix}{faker.lexify('??').upper()}"
    while icao_dep == icao_arr:
        icao_arr = f"{random_prefix}{faker.lexify('???').upper()}"

    airline_code = faker.lexify("???").upper()

    airline_page.create_airline(airline_code, "Booking Airline")
    airport_page.create_airport(icao_dep, "Dep Airport")
    airport_page.create_airport(icao_arr, "Arr Airport")

    # 2. Создаем рейс
    flight_num = str(random.randint(100, 999))
    flight_page.create_flight(flight_num, "2026-12-01", "10:00", 100)

    # 3. Создаем пассажира
    passport = f"{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"
    passenger_name = f"Ivan {unique_suffix}"
    passenger_page.create_passenger(passenger_name, passport, "FMS", "2020-01-01", "1990-01-01")

    # 4. Переходим к бронированию
    auth_page.open("/bookings/select/")

    # Ищем наш рейс в списке и кликаем "Забронировать"
    flight_page.search_flight(flight_num)
    from selenium.webdriver.common.by import By
    try:
        flight_row = flight_page.find(
            (By.XPATH, f"//article[contains(@class, 'flight-card-single') and contains(., '{flight_num}')]"))
        book_btn = flight_row.find_element(By.CSS_SELECTOR, "a[href*='/bookings/create/']")
        book_btn.click()

        # 5. Оформляем бронирование
        booking_page.create_booking(flight_num, passenger_name)
        msg, status = booking_page.get_alert_message()
        assert "успешн" in msg.lower(), f"Бронирование не удалось создать: {msg}"
    except Exception as e:
        pytest.fail(f"Не удалось найти рейс или забронировать: {e}")