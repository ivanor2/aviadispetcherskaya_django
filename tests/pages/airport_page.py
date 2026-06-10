from .base_page import BasePage
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException


class AirportPage(BasePage):
    @property
    def icao_field(self):
        return (By.ID, "id_icao_code")

    @property
    def name_field(self):
        return (By.ID, "id_name")

    @property
    def submit_btn(self):
        return (By.CSS_SELECTOR, "button[type='submit']")

    @property
    def airport_rows(self):
        return (By.CSS_SELECTOR, "table tbody tr")

    def go_to_list(self):
        self.open("/airports/")
        return self

    def go_to_create(self):
        self.open("/airports/create/")
        return self

    def create_airport(self, icao: str, name: str):
        self.go_to_create()
        self.input_text(self.icao_field, icao)
        self.input_text(self.name_field, name)
        self.click(self.submit_btn)
        self.wait_for_url("/airports/")
        return self

    def _find_card_across_pages(self, icao: str):
        """Ищет карточку аэропорта по ICAO на всех страницах списка."""
        self.go_to_list()
        while True:
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".airport-card-single")))
            cards = self.find_all((By.CSS_SELECTOR, ".airport-card-single"))
            for card in cards:
                if icao in card.text:
                    return card

            # Ищем кнопку "Вперёд"
            try:
                next_btn = self.driver.find_element(
                    By.XPATH, "//a[contains(@href,'?page=') and (contains(.,'Вперёд') or contains(.,'вперёд') or contains(.,'Next'))]"
                )
                next_btn.click()
                self.wait.until(EC.staleness_of(cards[0]))
            except NoSuchElementException:
                # Больше страниц нет
                return None

    def edit_airport(self, icao: str, new_name: str):
        target_card = self._find_card_across_pages(icao)
        if not target_card:
            raise Exception(f"Карточка аэропорта с ICAO {icao} не найдена")

        # Кликаем кнопку «Изменить» внутри найденной карточки
        edit_btn = target_card.find_element(By.CSS_SELECTOR, "a[href*='/edit/']")
        self.wait.until(EC.element_to_be_clickable(edit_btn)).click()

        self.input_text(self.name_field, new_name)
        self.click(self.submit_btn)
        self.wait_for_url("/airports/")
        return self

    def delete_airport(self, icao: str):
        target_card = self._find_card_across_pages(icao)
        if not target_card:
            return self

        try:
            delete_btn = target_card.find_element(
                By.CSS_SELECTOR, "button.btn-danger, form[action*='delete'] button[type='submit']"
            )
            delete_btn.click()
        except NoSuchElementException:
            return self

        try:
            self.driver.switch_to.alert.accept()
        except Exception:
            pass
        return self