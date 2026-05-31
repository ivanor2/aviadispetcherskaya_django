import pytest
from faker import Faker

faker = Faker("en_US")

def test_create_airport(auth_page, airport_page, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    icao = faker.lexify("????").upper()
    name = f"Airport {icao}"
    
    airport_page.create_airport(icao, name)
    
    if "/airports/" in auth_page.driver.current_url:
        airport_page.edit_airport(icao, f"{name} New")
        assert "успешн" in auth_page.get_alert_message()[0].lower() or "success" in auth_page.get_alert_message()[1]
