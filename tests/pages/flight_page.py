from .base_page import BasePage
from selenium.webdriver.common.by import By

class FlightPage(BasePage):
    @property
    def flight_number_field(self): return (By.ID, "id_flight_number")
    @property
    def dep_airport_select(self): return (By.ID, "id_departure_airport")
    @property
    def arr_airport_select(self): return (By.ID, "id_arrival_airport")
    @property
    def dep_date_field(self): return (By.ID, "id_departure_date")
    @property
    def dep_time_field(self): return (By.ID, "id_departure_time")
    @property
    def total_seats_field(self): return (By.ID, "id_total_seats")
    @property
    def save_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")
    @property
    def search_query(self): return (By.ID, "id_query")
    @property
    def search_type(self): return (By.ID, "id_search_type")
    @property
    def search_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")
    @property
    def flight_rows(self): return (By.CSS_SELECTOR, ".flight-row")
    @property
    def nav_flights_link(self): return (By.CSS_SELECTOR, "a[href*='/flights']")

    def go_to_create(self):
        self.open("/flights/create/")
        return self

    def create_flight(self, number: str, date: str, time: str, seats: int):
        self.go_to_create()
        self.input_text(self.flight_number_field, number)
        # Выбираем первый и второй элементы по индексу (пропуская дефолтный если нужно, пусть 1 и 2)
        from selenium.webdriver.support.ui import Select
        Select(self.find(self.dep_airport_select)).select_by_index(1)
        Select(self.find(self.arr_airport_select)).select_by_index(2)
        self.input_text(self.dep_date_field, date)
        self.input_text(self.dep_time_field, time)
        self.input_text(self.total_seats_field, str(seats))
        self.click(self.save_btn)
        self.wait_for_url("/flights/")
        return self

    def search_flight(self, query: str):
        self.open("/flights/")
        self.select_by_visible_text(self.search_type, "По номеру рейса")
        self.input_text(self.search_query, query)
        self.click(self.search_btn)
        return self

    def get_flight_count(self) -> int:
        try:
            return len(self.find_all(self.flight_rows))
        except:
            return 0

    def view_flight_details(self, flight_id: int):
        self.open(f"/flights/{flight_id}/")
        return self

    def delete_flight(self, flight_id: int):
        # Admin action, typically from detail or list page
        self.open(f"/flights/{flight_id}/")
        delete_btn = (By.CSS_SELECTOR, "button.btn-danger, form[action*='delete'] button[type='submit']")
        self.click(delete_btn)
        # Handle confirmation form or alert
        try:
            self.driver.switch_to.alert.accept()
        except:
            pass
        return self