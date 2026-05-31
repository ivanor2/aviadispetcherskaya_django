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
    def submit_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")
    @property
    def nav_passengers_link(self): return (By.CSS_SELECTOR, "a[href*='/passengers']")

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

    def search_passenger(self, query: str):
        self.open("/passengers/")
        search_input = (By.ID, "query")
        search_btn = (By.CSS_SELECTOR, "button[type='submit']")
        self.input_text(search_input, query)
        self.click(search_btn)
        return self

    def get_passenger_count(self) -> int:
        try:
            return len(self.find_all((By.CSS_SELECTOR, ".passenger-row, table tbody tr")))
        except:
            return 0

    def view_passenger_details(self, pk: int):
        self.open(f"/passengers/{pk}/")
        return self

    def delete_passenger(self, pk: int):
        self.open(f"/passengers/{pk}/")
        delete_btn = (By.CSS_SELECTOR, "button.btn-danger, form[action*='delete'] button")
        self.click(delete_btn)
        try:
            self.driver.switch_to.alert.accept()
        except:
            pass
        return self
