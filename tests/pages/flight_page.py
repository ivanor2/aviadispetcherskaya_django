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
    def save_btn(self): return (By.XPATH, "//button[contains(text(), 'Сохранить')]")
    @property
    def search_query(self): return (By.ID, "id_query")
    @property
    def search_type(self): return (By.ID, "id_search_type")
    @property
    def search_btn(self): return (By.XPATH, "//button[text()='🔍 Найти']")
    @property
    def flight_rows(self): return (By.CSS_SELECTOR, ".flight-row")
    @property
    def nav_flights_link(self): return (By.XPATH, "//a[contains(text(), 'Рейсы')]")

    def go_to_create(self):
        self.open("/flights/create/")
        return self

    def create_flight(self, number: str, date: str, time: str, seats: int):
        self.go_to_create()
        self.input_text(self.flight_number_field, number)
        # Выбираем первый доступный аэропорт, если список загружен
        self.select_by_visible_text(self.dep_airport_select, "UUEE")
        self.select_by_visible_text(self.arr_airport_select, "UUDD")
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