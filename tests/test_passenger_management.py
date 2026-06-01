import pytest
from faker import Faker

faker = Faker("ru_RU")

def test_create_and_list_passenger(auth_page, passenger_page, test_credentials):
    auth_page.login(test_credentials[0], test_credentials[1])
    
    fullname = faker.name()
    passport = f"{faker.random_number(digits=4, fix_len=True)}-{faker.random_number(digits=6, fix_len=True)}"
    
    # Create passenger
    passenger_page.create_passenger(
        fullname=fullname,
        passport=passport,
        issued_by="ФМС России",
        issue_date="2020-01-01",
        birth_date="1990-01-01"
    )
    
    # Search for created passenger by passport
    passenger_page.search_passenger(passport)
    assert passenger_page.get_passenger_count() >= 1, "Созданный пассажир не найден"

def test_guest_cannot_access_passengers(auth_page, passenger_page):
    passenger_page.go_to_create()
    assert "/login/" in auth_page.driver.current_url, "Гость смог зайти на страницу создания пассажира"

# Additional tests for view details and delete can be added if DB seeding is available
