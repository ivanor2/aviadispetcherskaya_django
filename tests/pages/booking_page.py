from .base_page import BasePage
from selenium.webdriver.common.by import By
import time


class BookingPage(BasePage):
    @property
    def submit_btn(self):
        return (By.CSS_SELECTOR, "button[type='submit']")

    def create_booking(self, search_text: str, class_type: str = "economy"):
        """Заполняет форму бронирования на уже открытой странице /bookings/create/<id>/.

        Выбирает пассажира по тексту search_text через TomSelect (или нативный select),
        устанавливает класс обслуживания и отправляет форму.
        """
        self.wait.until(lambda d: "/bookings/create/" in d.current_url)
        self.wait.until(lambda d: d.execute_script(
            "return document.querySelector('select[name=\"passenger_ids\"]') !== null;"
        ))
        time.sleep(1.5)

        passenger_script = f"""
        (function() {{
            var selectEl = document.querySelector('select[name="passenger_ids"]');
            if (!selectEl) return 'ERROR: select not found';

            if (selectEl.tomselect) {{
                var ts = selectEl.tomselect;
                var targetKey = null;
                for (var key in ts.options) {{
                    if (ts.options[key].text.includes('{search_text}')) {{
                        targetKey = key;
                        break;
                    }}
                }}
                if (targetKey !== null && targetKey !== '') {{
                    ts.setValue(targetKey);
                    return 'OK: TomSelect key=' + targetKey;
                }}
                return 'ERROR: passenger not found in TomSelect';
            }} else {{
                for (var i = 0; i < selectEl.options.length; i++) {{
                    if (selectEl.options[i].text.includes('{search_text}')) {{
                        selectEl.selectedIndex = i;
                        selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'OK: Native index=' + i;
                    }}
                }}
                return 'ERROR: passenger not found in native';
            }}
        }})();
        """
        self.driver.execute_script(passenger_script)

        class_script = f"""
        (function() {{
            var selectEl = document.querySelector('select[name="class_type"]');
            if (!selectEl) return 'ERROR: class select not found';

            if (selectEl.tomselect) {{
                var ts = selectEl.tomselect;
                var targetKey = null;
                for (var key in ts.options) {{
                    if (key === '{class_type}' || ts.options[key].text.toLowerCase().includes('{class_type}')) {{
                        targetKey = key;
                        break;
                    }}
                }}
                if (targetKey !== null) {{
                    ts.setValue(targetKey);
                    return 'OK: TomSelect class=' + targetKey;
                }}
            }} else {{
                for (var i = 0; i < selectEl.options.length; i++) {{
                    if (selectEl.options[i].value === '{class_type}') {{
                        selectEl.selectedIndex = i;
                        selectEl.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        return 'OK: Native class=' + selectEl.options[i].value;
                    }}
                }}
            }}
            return 'ERROR: class not found';
        }})();
        """
        self.driver.execute_script(class_script)

        time.sleep(0.5)
        self.click(self.submit_btn)
        return self