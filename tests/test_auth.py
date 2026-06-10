import pytest
from faker import Faker

faker = Faker("ru_RU")


def test_successful_registration_and_login(auth_page):
    """Регистрирует нового пользователя и проверяет успешный вход.

    После регистрации ожидает сообщение об успехе, затем выполняет
    вход и убеждается, что панель управления отображается.
    """
    username = f"test_{faker.user_name()}"
    password = "TestPass123!"

    auth_page.register(username, password)
    msg, status = auth_page.get_alert_message()

    assert status == "success", f"Ожидался успех регистрации, получено: {msg}"

    auth_page.login(username, password)
    assert auth_page.is_logged_in(), "После входа не отображается панель управления"


def test_logout_redirects_to_login(auth_page):
    """Проверяет, что выход из системы перенаправляет на страницу входа.

    Регистрирует пользователя, выполняет вход и нажимает «Выход»,
    затем убеждается, что URL содержит /login/.
    """
    username = f"test_{faker.user_name()}"
    password = "TestPass123!"
    auth_page.register(username, password)

    auth_page.wait.until(lambda d: "/login/" in d.current_url)

    auth_page.login(username, password)
    auth_page.logout()
    assert "/login/" in auth_page.driver.current_url, "После выхода не произошел редирект на страницу логина"


def test_login_with_wrong_password(auth_page):
    """Проверяет отображение ошибки при неверном пароле.

    Выполняет вход с несуществующим пользователем и убеждается,
    что появляется сообщение об ошибке аутентификации.
    """
    auth_page.login("nonexistent_user", "WrongPass!", expect_success=False)
    msg, status = auth_page.get_alert_message()
    assert status == "error", "При неверном пароле не появилась ошибка"
    assert "Неверный логин или пароль" in msg or "Ошибка" in msg