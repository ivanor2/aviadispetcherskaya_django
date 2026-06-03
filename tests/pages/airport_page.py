from .base_page import BasePage
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC


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

    def edit_airport(self, icao: str, new_name: str):
        self.go_to_list()
        # Ждем появления карточек
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".airport-card-single")))

        # Ищем нужную карточку в цикле
        cards = self.find_all((By.CSS_SELECTOR, ".airport-card-single"))
        target_card = None
        for card in cards:
            if icao in card.text:
                target_card = card
                break

        if not target_card:
            raise Exception(f"Карточка аэропорта с ICAO {icao} не найдена")

        # Кликаем кнопку "Изменить" ВНУТРИ найденной карточки
        edit_btn = target_card.find_element(By.CSS_SELECTOR, "a[href*='/edit/']")
        self.wait.until(EC.element_to_be_clickable(edit_btn)).click()

        self.input_text(self.name_field, new_name)
        self.click(self.submit_btn)
        self.wait_for_url("/airports/")
        return self

    def delete_airport(self, icao: str):
        self.go_to_list()
        cards = self.find_all((By.CSS_SELECTOR, ".airport-card-single, table tbody tr"))
        for card in cards:
            if icao in card.text:
                delete_btn = card.find_element(By.CSS_SELECTOR,
                                               "button.btn-danger, form[action*='delete'] button[type='submit']")
                delete_btn.click()
                break
        try:
            self.driver.switch_to.alert.accept()
        except:
            pass
        return self