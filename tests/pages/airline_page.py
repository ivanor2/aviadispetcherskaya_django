from .base_page import BasePage
from selenium.webdriver.common.by import By

class AirlinePage(BasePage):
    @property
    def code_field(self): return (By.ID, "id_code")
    @property
    def name_field(self): return (By.ID, "id_name")
    @property
    def submit_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")
    @property
    def airline_rows(self): return (By.CSS_SELECTOR, "table tbody tr")

    def go_to_list(self):
        self.open("/airlines/")
        return self

    def go_to_create(self):
        self.open("/airlines/create/")
        return self

    def create_airline(self, code: str, name: str):
        self.go_to_create()
        self.input_text(self.code_field, code)
        self.input_text(self.name_field, name)
        self.click(self.submit_btn)
        self.wait_for_url("/airlines/")
        return self

    def edit_airline(self, code: str, new_name: str):
        self.open(f"/airlines/{code}/edit/")
        self.input_text(self.name_field, new_name)
        self.click(self.submit_btn)
        self.wait_for_url("/airlines/")
        return self

    def delete_airline(self, code: str):
        # Admin action - assumed POST to delete URL or button in list
        self.go_to_list()
        cards = self.find_all((By.CSS_SELECTOR, ".airline-card-single, table tbody tr"))
        for card in cards:
            if code in card.text:
                delete_btn = card.find_element(By.CSS_SELECTOR, "button.btn-danger, form[action*='delete'] button[type='submit']")
                delete_btn.click()
                break
        # Accept alert if there is one
        try:
            self.driver.switch_to.alert.accept()
        except:
            pass
        return self
