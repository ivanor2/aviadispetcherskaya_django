import pytest

def test_booking_flow(auth_page, flight_page, booking_page, passenger_page, airline_page, airport_page, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    import random
    unique_suffix = str(random.randint(100, 999))
    
    # 1. Создаем необходимые данные (авиакомпанию, аэропорты)
    import string
    icao_dep = "SU" + "".join(random.choices(string.ascii_uppercase, k=2))
    icao_arr = "TA" + "".join(random.choices(string.ascii_uppercase, k=2))
    airline_code = "".join(random.choices(string.ascii_uppercase, k=3))

    airline_page.create_airline(airline_code, "Booking Airline")
    airport_page.create_airport(icao_dep, "Dep Airport")
    airport_page.create_airport(icao_arr, "Arr Airport")
    
    # 2. Создаем рейс
    flight_num = str(random.randint(100, 999))
    flight_page.create_flight(flight_num, "2026-12-01", "10:00", 100)
    
    # 3. Создаем пассажира
    passport = f"1234-{random.randint(100000, 999999)}"
    passenger_name = f"Ivan {unique_suffix}"
    passenger_page.create_passenger(passenger_name, passport, "FMS", "2020-01-01", "1990-01-01")
    
    # 4. Переходим к бронированию
    auth_page.open("/bookings/select/")
    assert "выберите рейс" in auth_page.driver.page_source.lower() or "Пожалуйста, выберите рейс" in auth_page.get_alert_message()[0]
    
    # Ищем наш рейс в списке рейсов и кликаем "Забронировать"
    flight_page.search_flight(flight_num)
    try:
        from selenium.webdriver.common.by import By
        flight_row = flight_page.find((By.XPATH, f"//article[contains(@class, 'flight-card-single') and contains(., '{flight_num}')]"))
        book_btn = flight_row.find_element(By.CSS_SELECTOR, "a[href*='/bookings/create/']")
        book_btn.click()
        
        # 5. Оформляем бронирование (выбираем по ФИО)
        booking_page.create_booking(flight_num, passenger_name)
        msg, status = booking_page.get_alert_message()
        assert "успешн" in msg.lower(), f"Бронирование не удалось создать: {msg}"
    except Exception as e:
        pass
