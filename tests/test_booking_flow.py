import random
import time
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
        icao_arr = f"{random_prefix}{faker.lexify('??').upper()}"

    airline_code = faker.lexify("???").upper()

    airline_page.create_airline(airline_code, "Booking Airline")
    airport_page.create_airport(icao_dep, "Dep Airport")
    airport_page.create_airport(icao_arr, "Arr Airport")

    flight_num = str(random.randint(100, 999))
    # Передаем airline_code, чтобы тест выбрал именно эту авиакомпанию
    flight_page.create_flight(flight_num, "2026-12-01", "10:00", 100, airline_code=airline_code)

    passport = f"{random.randint(1000, 9999)}-{random.randint(100000, 999999)}"
    passenger_name = f"Ivan {unique_suffix}"
    passenger_page.create_passenger(passenger_name, passport, "FMS", "2020-01-01", "1990-01-01")

    # Переходим к выбору рейса
    auth_page.open("/bookings/select/")
    time.sleep(1)

    flight_page.search_flight(f"{airline_code}-{flight_num}")
    time.sleep(1)

    from selenium.webdriver.common.by import By
    try:
        flight_row = flight_page.find(
            (By.XPATH, f"//article[contains(@class, 'flight-card-single') and contains(., '{flight_num}')]"))
        book_btn = flight_row.find_element(By.CSS_SELECTOR, "a[href*='/bookings/create/']")

        # Кликаем "Купить" -> Браузер сам переходит на /bookings/create/<реальный_ID>/
        book_btn.click()
        time.sleep(2)  # Ждем, пока страница бронирования полностью загрузится

        # ✅ Вызываем create_booking, передавая УНИКАЛЬНЫЙ СУФФИКС для надежного поиска в JS
        # Метод сам поймет, что мы уже на нужной странице, и не будет делать лишний open()
        booking_page.create_booking(unique_suffix)

        time.sleep(2)  # Ждем обработки формы

        msg, status = booking_page.get_alert_message()
        assert "успешн" in msg.lower() or status == "success", f"Бронирование не удалось создать: {msg}"

    except Exception as e:
        pytest.fail(f"Не удалось найти рейс или забронировать: {e}")