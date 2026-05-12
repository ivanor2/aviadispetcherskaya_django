from .base_page import BasePage
from selenium.webdriver.common.by import By

class AuthPage(BasePage):
    @property
    def username_field(self): return (By.ID, "id_username")
    @property
    def password_field(self): return (By.ID, "id_password")
    @property
    def password_confirm_field(self): return (By.ID, "id_password_confirm")
    @property
    def login_btn(self): return (By.CSS_SELECTOR, ".btn-lg")
    @property
    def register_btn(self): return (By.CSS_SELECTOR, ".btn-block")
    @property
    def logout_link(self): return (By.CSS_SELECTOR, ".btn-logout")
    @property
    def dashboard_title(self): return (By.CSS_SELECTOR, ".dashboard-header h1")

    def register(self, username, password):
        self.open("/register/")
        self.input_text(self.username_field, username)
        self.input_text(self.password_field, password)
        self.input_text(self.password_confirm_field, password)
        self.click(self.register_btn)
        return self

    def login(self, username, password):
        self.open("/login/")
        self.input_text(self.username_field, username)
        self.input_text(self.password_field, password)
        self.click(self.login_btn)
        self.wait_for_url("/")
        return self

    def logout(self):
        self.click(self.logout_link)
        self.wait_for_url("/login/")
        return self

    def is_logged_in(self) -> bool:
        try:
            return self.dashboard_title is not None and self.find(self.dashboard_title).is_displayed()
        except:
            return False