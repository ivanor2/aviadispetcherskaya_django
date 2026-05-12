import pytest
from faker import Faker

faker = Faker("ru_RU")

def test_successful_registration_and_login(auth_page):
    username = f"test_{faker.user_name()}"
    password = "TestPass123!"

    # ARRANGE & ACT
    auth_page.register(username, password)
    msg, status = auth_page.get_alert_message()

    # ASSERT
    assert status == "success", f"Ожидался успех регистрации, получено: {msg}"

    auth_page.login(username, password)
    assert auth_page.is_logged_in(), "После входа не отображается панель управления"

def test_logout_redirects_to_login(auth_page):
    username = f"test_{faker.user_name()}"
    password = "TestPass123!"
    auth_page.register(username, password)
    auth_page.login(username, password)

    auth_page.logout()
    assert "/login/" in auth_page.driver.current_url, "После выхода не произошел редирект на страницу логина"

def test_login_with_wrong_password(auth_page):
    auth_page.login("nonexistent_user", "WrongPass!")
    msg, status = auth_page.get_alert_message()
    assert status == "error", "При неверном пароле не появилась ошибка"
    assert "Неверный логин или пароль" in msg or "Ошибка" in msg