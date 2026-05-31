from .base_page import BasePage
from selenium.webdriver.common.by import By

class BookingPage(BasePage):
    @property
    def passenger_select(self): return (By.ID, "id_passenger_ids")
    @property
    def baggage_checkbox(self): return (By.ID, "id_baggage_allowed")
    @property
    def payment_type_select(self): return (By.ID, "id_payment_type")
    @property
    def class_type_select(self): return (By.ID, "id_class_type")
    @property
    def submit_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")
    
    # Connection fields
    @property
    def connection_booking_code(self): return (By.ID, "id_booking_code")
    @property
    def connection_flight_id(self): return (By.ID, "id_flight_id")

    def go_to_create(self, flight_id: int):
        self.open(f"/bookings/create/{flight_id}/")
        return self

    def create_booking(self, flight_id: int, passenger_id: str, class_type: str = "economy"):
        self.go_to_create(flight_id)
        # Assuming passenger_ids is a multi-select, select_by_value or clicking the option
        # For simplicity, let's use select_by_visible_text or similar, but passenger_id might be value
        from selenium.webdriver.support.ui import Select
        el = self.find(self.passenger_select)
        Select(el).select_by_value(passenger_id)
        
        self.select_by_visible_text(self.class_type_select, class_type if class_type != "economy" else "Эконом") # Adjust if English options
        self.click(self.submit_btn)
        return self

    def go_to_add_connection(self):
        self.open("/bookings/add-connection/")
        return self

    def add_connection(self, booking_code: str, flight_id: str):
        self.go_to_add_connection()
        self.input_text(self.connection_booking_code, booking_code)
        self.input_text(self.connection_flight_id, flight_id)
        self.click(self.submit_btn)
        return self
