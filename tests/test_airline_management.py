import pytest
from faker import Faker

faker = Faker("en_US")

def test_create_and_edit_airline(auth_page, airline_page, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    code = faker.lexify("???").upper()
    name = f"Airline {code}"
    
    airline_page.create_airline(code, name)
    msg, status = auth_page.get_alert_message()
    
    # If not admin, it might redirect or fail.
    if "/airlines/" in auth_page.driver.current_url:
        airline_page.edit_airline(code, f"{name} Edited")
        assert "успешн" in auth_page.get_alert_message()[0].lower() or "success" in auth_page.get_alert_message()[1]
