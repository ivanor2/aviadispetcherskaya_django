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

    def create_booking(self, flight_id: str, passenger_name: str, class_type: str = "economy"):
        self.go_to_create(flight_id)
        
        # Select passenger from TomSelect by Name
        script = f"""
        var ts = document.getElementById('id_passenger_ids').tomselect;
        var matchValue = null;
        for (var key in ts.options) {{
            if (ts.options[key].text.includes('{passenger_name}')) {{
                matchValue = key;
                break;
            }}
        }}
        if (matchValue) {{
            ts.setValue(matchValue);
        }}
        """
        self.driver.execute_script(script)
        
        # Or if class_type is not economy, we need to click it. Usually standard Select works for it if it's not TomSelect.
        # But if it is TomSelect:
        class_script = f"""
        var ts = document.getElementById('id_class_type');
        if(ts && ts.tomselect) {{
             var keys = Object.keys(ts.tomselect.options);
             ts.tomselect.setValue(keys[0]);
        }} else if (ts) {{
             ts.value = '{class_type}';
        }}
        """
        self.driver.execute_script(class_script)
        
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
