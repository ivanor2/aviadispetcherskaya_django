import pytest

def test_booking_flow(auth_page, flight_page, booking_page, passenger_page, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    # For now, just test access to the flight select page
    auth_page.open("/bookings/select/")
    assert "выберите рейс" in auth_page.driver.page_source.lower() or "Пожалуйста, выберите рейс" in auth_page.get_alert_message()[0]

    # Ideally we create a flight, create a passenger, and then create a booking
    # flight_page.create_flight(...)
    # passenger_page.create_passenger(...)
    # booking_page.create_booking(...)
    # Assert success message.
