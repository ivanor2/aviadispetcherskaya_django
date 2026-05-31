import os
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options

from tests.pages.auth_page import AuthPage
from tests.pages.flight_page import FlightPage
from tests.pages.passenger_page import PassengerPage
from tests.pages.booking_page import BookingPage
from tests.pages.airline_page import AirlinePage
from tests.pages.airport_page import AirportPage
import subprocess
import time
import sys

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

@pytest.fixture(scope="session", autouse=True)
def start_dev_server():
    process = subprocess.Popen(
        [sys.executable, "manage.py", "runserver", "8000"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(3)
    yield
    process.terminate()

@pytest.fixture
def test_credentials():
    """Возвращает логин и пароль для E2E тестов из переменных окружения"""
    username = os.getenv("TEST_USERNAME", "aboba")
    password = os.getenv("TEST_PASSWORD", "123456q!")
    return username, password

@pytest.fixture(scope="session")
def browser():
    options = Options()
    options.add_argument("--start-maximized")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    yield driver
    driver.quit()

@pytest.fixture
def wait(browser):
    return WebDriverWait(browser, 10)

@pytest.fixture(autouse=True)
def clear_session(browser, base_url):
    """Очистка куки и переход на главную перед каждым тестом для изоляции"""
    browser.delete_all_cookies()
    browser.get(f"{base_url}/login/")
    yield

@pytest.fixture
def base_url():
    return BASE_URL



@pytest.fixture
def auth_page(browser, wait):
    return AuthPage(browser, wait)

@pytest.fixture
def flight_page(browser, wait):
    return FlightPage(browser, wait)

@pytest.fixture
def passenger_page(browser, wait):
    return PassengerPage(browser, wait)

@pytest.fixture
def booking_page(browser, wait):
    return BookingPage(browser, wait)

@pytest.fixture
def airline_page(browser, wait):
    return AirlinePage(browser, wait)

@pytest.fixture
def airport_page(browser, wait):
    return AirportPage(browser, wait)