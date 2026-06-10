from .base_page import BasePage
from selenium.webdriver.common.by import By
import time


class FlightPage(BasePage):
    @property
    def flight_number_field(self):
        return (By.ID, "id_flight_number")

    @property
    def dep_airport_select(self):
        return (By.ID, "id_departure_airport")

    @property
    def arr_airport_select(self):
        return (By.ID, "id_arrival_airport")

    @property
    def dep_date_field(self):
        return (By.ID, "id_departure_date")

    @property
    def dep_time_field(self):
        return (By.ID, "id_departure_time")

    @property
    def total_seats_field(self):
        return (By.ID, "id_total_seats")

    @property
    def save_btn(self):
        return (By.CSS_SELECTOR, "button[type='submit']")

    @property
    def search_query(self):
        return (By.ID, "id_query")

    @property
    def search_type(self):
        return (By.ID, "id_search_type")

    @property
    def search_btn(self):
        return (By.CSS_SELECTOR, "form.search-form button[type='submit']")

    @property
    def flight_rows(self):
        return (By.CSS_SELECTOR, ".flight-card-single, .flight-row")

    @property
    def nav_flights_link(self):
        return (By.CSS_SELECTOR, "a[href*='/flights']")

    def go_to_create(self):
        self.open("/flights/create/")
        return self

    def create_flight(self, number: str, date: str, time: str, seats: int, airline_code: str = None):
        self.go_to_create()

        self.wait.until(lambda d: d.execute_script(
            "return document.getElementById('id_airline')?.tomselect !== undefined"
        ))

        self.input_text(self.flight_number_field, number)

        def select_tomselect_by_code(select_id, code):
            script = f"""
                var ts = document.getElementById('{select_id}').tomselect;
                if (!ts) return false;
                for (var key in ts.options) {{
                    if (ts.options[key].text.includes('{code}')) {{
                        ts.setValue(key);
                        return true;
                    }}
                }}
                return false;
            """
            for _ in range(20):
                if self.driver.execute_script(script):
                    return True
                time.sleep(0.3)
            raise Exception(f"TomSelect '{select_id}' не содержит опции с '{code}'")

        def select_tomselect(select_id, prefer_index=0):
            script = f"""
                var ts = document.getElementById('{select_id}').tomselect;
                if (!ts) return false;
                var keys = Object.keys(ts.options).filter(k => k !== '' && k !== null);
                if (keys.length === 0) return false;
                var idx = Math.min({prefer_index}, keys.length - 1);
                ts.setValue(keys[idx]);
                return true;
            """
            for _ in range(20):
                if self.driver.execute_script(script):
                    return True
                time.sleep(0.3)
            raise Exception(f"TomSelect '{select_id}' не содержит опций")

        if airline_code:
            select_tomselect_by_code('id_airline', airline_code)
        else:
            select_tomselect('id_airline', 0)

        select_tomselect('id_departure_airport', 0)
        select_tomselect('id_arrival_airport', 1)

        self._set_input_value('id_departure_date', date)
        self._set_input_value('id_departure_time', time)
        self._set_input_value('id_arrival_time', '16:30')

        self.input_text(self.total_seats_field, str(seats))
        self._set_input_value('id_base_price', '100.00')
        self._set_input_value('id_baggage_price', '20.00')

        self.click(self.save_btn)
        self.wait_for_url("/flights/")
        return self

    def _set_input_value(self, element_id: str, value: str):
        self.driver.execute_script(f"""
            var el = document.getElementById('{element_id}');
            var nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(el, '{value}');
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
        """)

    def search_flight(self, query: str):
        self.open("/flights/")
        self.select_by_visible_text(self.search_type, "По номеру рейса")
        self.input_text(self.search_query, query)
        self.click(self.search_btn)
        return self

    def click_book_button(self, flight_number: str):
        """Находит карточку рейса по номеру и кликает кнопку бронирования.

        Предполагается, что перед вызовом уже выполнен search_flight(),
        а страница отображает результаты поиска.
        """
        flight_card_locator = (
            By.XPATH,
            f"//article[contains(@class, 'flight-card-single') and contains(., '{flight_number}')]"
        )
        flight_card = self.find(flight_card_locator)
        book_btn = flight_card.find_element(By.CSS_SELECTOR, "a[href*='/bookings/create/']")
        book_btn.click()
        self.wait.until(lambda d: "/bookings/create/" in d.current_url)
        return self

    def get_flight_count(self) -> int:
        try:
            return len(self.find_all(self.flight_rows))
        except Exception:
            return 0

    def view_flight_details(self, flight_id: int):
        self.open(f"/flights/{flight_id}/")
        return self

    def delete_flight(self, flight_id: int):
        self.open(f"/flights/{flight_id}/")
        delete_btn = (By.CSS_SELECTOR, "button.btn-danger, form[action*='delete'] button[type='submit']")
        self.click(delete_btn)
        try:
            self.driver.switch_to.alert.accept()
        except Exception:
            pass
        return self