from .base_page import BasePage
from selenium.webdriver.common.by import By
import time


class BookingPage(BasePage):
    @property
    def submit_btn(self): return (By.CSS_SELECTOR, "button[type='submit']")

    def create_booking(self, search_text: str, class_type: str = "economy"):
        # ✅ ВАЖНО: Мы УЖЕ на странице /bookings/create/<id>/ после клика в тесте.
        # Не делаем self.open(), чтобы не потерять реальный ID рейса и не уйти на 404.

        # Ждем, пока форма и селекты загрузятся
        self.wait.until(lambda d: "/bookings/create/" in d.current_url)
        self.wait.until(lambda d: d.execute_script(
            "return document.querySelector('select[name=\"passenger_ids\"]') !== null;"
        ))
        time.sleep(1.5)  # Даем время TomSelect полностью инициализироваться

        # 1. Выбор пассажира
        # ✅ ИСПОЛЬЗУЕМ ОРИГИНАЛЬНЫЙ КЛЮЧ из ts.options, чтобы избежать проблем с типами (str vs int)
        passenger_script = f"""
        (function() {{
            var selectEl = document.querySelector('select[name="passenger_ids"]');
            if (!selectEl) return 'ERROR: select not found';

            if (selectEl.tomselect) {{
                var ts = selectEl.tomselect;
                var targetKey = null;
                for (var key in ts.options) {{
                    if (ts.options[key].text.includes('{search_text}')) {{
                        targetKey = key; // Сохраняем оригинальный ключ (число или строка)
                        break;
                    }}
                }}
                if (targetKey !== null && targetKey !== '') {{
                    ts.setValue(targetKey);
                    return 'OK: TomSelect key=' + targetKey;
                }}
                return 'ERROR: passenger not found in TomSelect';
            }} else {{
                // Fallback для нативного select
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
        res_p = self.driver.execute_script(passenger_script)
        print(f"🔹 [BookingPage] Выбор пассажира: {res_p}")

        # 2. Выбор класса обслуживания
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
        res_c = self.driver.execute_script(class_script)
        print(f"🔹 [BookingPage] Выбор класса: {res_c}")

        # Небольшая пауза перед сабмитом, чтобы UI успел отрисоваться
        time.sleep(0.5)
        self.click(self.submit_btn)
        return self