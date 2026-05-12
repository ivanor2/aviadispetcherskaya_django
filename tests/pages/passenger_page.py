from .base_page import BasePage
from selenium.webdriver.common.by import By

class PassengerPage(BasePage):
    @property
    def fullname_field(self): return (By.ID, "id_full_name")
    @property
    def passport_field(self): return (By.ID, "id_passport_number")
    @property
    def issued_by_field(self): return (By.ID, "id_passport_issued_by")
    @property
    def issue_date_field(self): return (By.ID, "id_passport_issue_date")
    @property
    def birth_date_field(self): return (By.ID, "id_birth_date")
    @property
    def submit_btn(self): return (By.XPATH, "//button[contains(text(), 'Зарегистрировать')]")
    @property
    def nav_passengers_link(self): return (By.XPATH, "//a[contains(text(), 'Пассажиры')]")

    def go_to_create(self):
        self.open("/passengers/create/")
        return self

    def create_passenger(self, fullname: str, passport: str, issued_by: str, issue_date: str, birth_date: str):
        self.go_to_create()
        self.input_text(self.fullname_field, fullname)
        self.input_text(self.passport_field, passport)
        self.input_text(self.issued_by_field, issued_by)
        self.input_text(self.issue_date_field, issue_date)
        self.input_text(self.birth_date_field, birth_date)
        self.click(self.submit_btn)
        self.wait_for_url("/passengers/")
        return self
