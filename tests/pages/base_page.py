from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.select import Select
import os

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")

class BasePage:
    def __init__(self, driver, wait: WebDriverWait):
        self.driver = driver
        self.wait = wait

    def open(self, path: str):
        full_url = path if path.startswith("http") else f"{BASE_URL}{path}"
        self.driver.get(full_url)
        return self

    def find(self, locator):
        return self.wait.until(EC.presence_of_element_located(locator))

    def find_all(self, locator):
        return self.wait.until(EC.presence_of_all_elements_located(locator))

    def click(self, locator):
        el = self.wait.until(EC.element_to_be_clickable(locator))
        el.click()
        return self

    def input_text(self, locator, text):
        el = self.find(locator)
        el.clear()
        el.send_keys(text)
        return self

    def select_by_visible_text(self, locator, text):
        el = self.find(locator)
        Select(el).select_by_visible_text(text)
        return self

    def get_text(self, locator):
        return self.find(locator).text

    def get_alert_message(self):
        try:
            success = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-success")))
            return success.text, "success"
        except:
            try:
                error = self.wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, ".alert-error")))
                return error.text, "error"
            except:
                return "", "none"


    def wait_for_url(self, expected_path):
        """Ожидание, что URL содержит expected_path (без /create/ на конце)"""
        expected = expected_path.strip("/")

        def check_url(driver):
            url = driver.current_url
            # Нормализуем: убираем query-параметры и trailing slash
            clean = url.split("?")[0].rstrip("/")
            if expected == "":
                return clean == BASE_URL.rstrip("/")
            return clean.endswith("/" + expected) or clean == expected

        self.wait.until(check_url, message=f"URL не стал содержать '{expected_path}'. Текущий: {self.driver.current_url}")
        return self