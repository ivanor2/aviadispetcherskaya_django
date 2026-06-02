from .base_page import BasePage
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

class AirportPage(BasePage):
    @property
    def icao_field(self): return (By.ID, "id_icao_code")
    @property
    def name_field(self): return (By.ID, "id_name")
    @property
    def submit_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")
    @property
    def airport_rows(self): return (By.CSS_SELECTOR, "table tbody tr")

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
        # Переходим на список и ждём появления карточки с нужным ICAO
        self.go_to_list()

        # ✅ Ждём, пока в DOM появится карточка именно с нашим ICAO (до 15 сек)
        card_locator = (By.XPATH, f"//article[contains(@class, 'airport-card-single') and contains(., '{icao}')]")
        card = self.wait.until(EC.presence_of_element_located(card_locator))

        # ✅ Кликаем кнопку "Изменить" ВНУТРИ этой карточки
        edit_btn = card.find_element(By.CSS_SELECTOR, "a[href*='/edit/']")
        self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "a[href*='/edit/']"))).click()

        # Теперь мы на /airports/<id>/edit/ — поле name точно есть
        self.input_text(self.name_field, new_name)
        self.click(self.submit_btn)
        self.wait_for_url("/airports/")
        return self

    def delete_airport(self, icao: str):
        # Find row/card by ICAO and click delete
        self.go_to_list()
        cards = self.find_all((By.CSS_SELECTOR, ".airport-card-single, table tbody tr"))
        for card in cards:
            if icao in card.text:
                delete_btn = card.find_element(By.CSS_SELECTOR, "button.btn-danger, form[action*='delete'] button[type='submit']")
                delete_btn.click()
                break
        try:
            self.driver.switch_to.alert.accept()
        except:
            pass
        return self
