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

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

@pytest.fixture(scope="session")
def browser():
    options = Options()
    options.add_argument("--start-maximized")
    # options.add_argument("--headless=new")  # Раскомментируйте для CI
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