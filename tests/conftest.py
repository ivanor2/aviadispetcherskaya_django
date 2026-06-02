import os
import random
from datetime import datetime, timedelta

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

from faker import Faker

faker = Faker("en_US")

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")
prefixes = ['AG', 'AN', 'AY', 'BG', 'BI', 'DA', 'DB', 'DF', 'DG', 'DI', 'DN', 'DR', 'DT', 'DX', 'EB', 'ED', 'EE', 'EF', 'EG', 'EH', 'EI',
            'EK', 'EL', 'EN', 'EP', 'ES', 'ET', 'EV', 'EY', 'FA', 'FB', 'FC', 'FD', 'FE', 'FG', 'FH', 'FI', 'FJ', 'FK', 'FL', 'FM', 'FN',
            'FO', 'FP', 'FQ', 'FS', 'FT', 'FV', 'FW', 'FX', 'FY', 'FZ', 'GA', 'GB', 'GC', 'GE', 'GF', 'GG', 'GL', 'GM', 'GO', 'GQ', 'GS',
            'GU', 'GV', 'HA', 'HB', 'HC', 'HD', 'HE', 'HF', 'HH', 'HK', 'HL', 'HR', 'HS', 'HT', 'HU', 'K', 'LA', 'LB', 'LC', 'LD', 'LE',
            'LF', 'LG', 'LH', 'LI', 'LJ', 'LK', 'LL', 'LM', 'LN', 'LO', 'LP', 'LQ', 'LR', 'LS', 'LT', 'LU', 'LV', 'LW', 'LX', 'LY', 'LZ',
            'MB', 'MD', 'MG', 'MH', 'MK', 'MM', 'MN', 'MP', 'MR', 'MS', 'MT', 'MU', 'MW', 'MY', 'MZ', 'NC', 'NF', 'NG', 'NI', 'NL', 'NS',
            'NT', 'NV', 'NW', 'NZ', 'OA', 'OB', 'OE', 'OI', 'OJ', 'OK', 'OL', 'OM', 'OO', 'OP', 'OR', 'OS', 'OT', 'OY', 'PA', 'PB', 'PC',
            'PF', 'PG', 'PH', 'PJ', 'PK', 'PL', 'PM', 'PO', 'PP', 'PT', 'PW', 'RC', 'RJ', 'RK', 'RO', 'RP', 'SA', 'SB', 'SC', 'SD', 'SE',
            'SF', 'SG', 'SK', 'SL', 'SM', 'SN', 'SO', 'SP', 'SS', 'SU', 'SV', 'SW', 'SY', 'TA', 'TB', 'TD', 'TF', 'TG', 'TI', 'TJ', 'TK',
            'TL', 'TN', 'TQ', 'TR', 'TT', 'TU', 'TV', 'TX', 'U', 'UA', 'UB', 'UC', 'UD', 'UG', 'UK', 'UM', 'UT', 'VA', 'VC', 'VD', 'VE',
            'VG', 'VH', 'VI', 'VL', 'VM', 'VN', 'VO', 'VQ', 'VR', 'VT', 'VV', 'VY', 'WA', 'WB', 'WI', 'WM', 'WP', 'WQ', 'WR', 'WS',
             'ZK', 'ZM']
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
    driver = webdriver.Chrome(options=options)
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

@pytest.fixture
def random_prefix():
    return random.choice(prefixes)

@pytest.fixture
def valid_flight_data():
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return {
        "number": faker.random_number(digits=3),
        "date": tomorrow,
        "time": "14:30",
        "seats": 150
    }



