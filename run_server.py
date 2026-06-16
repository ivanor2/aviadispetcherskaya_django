# run_server.py
import os
import sys
from pathlib import Path


def get_working_dir():
    """Определяет директорию, где физически находится запущенный файл (.exe или .py)"""
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent


def main():
    working_dir = get_working_dir()

    # Делаем рабочую директорию текущей (чтобы decouple нашел .env файл рядом с exe)
    os.chdir(str(working_dir))

    # Добавляем пути для корректной работы импортов (на случай, если что-то пошло не так)
    if getattr(sys, 'frozen', False):
        sys.path.insert(0, str(Path(sys._MEIPASS)))

    # Устанавливаем переменную окружения для Django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'django_app.settings')

    from django.core.management import execute_from_command_line

    # Если аргументы командной строки не переданы, запускаем сервер по умолчанию
    if len(sys.argv) < 2:
        sys.argv = ['run_server.py', 'runserver', '127.0.0.1:8000', '--noreload']

    print("🚀 Запуск АРМ Диспетчера...")
    print(f"   Рабочая директория: {working_dir}")
    print(f"   Аргументы: {' '.join(sys.argv)}")

    # Проверяем наличие .env для информативности
    if (working_dir / '.env').exists():
        print("   ✅ Файл .env найден и будет использован.")
    else:
        print("   ⚠️ Файл .env не найден (используются значения по умолчанию).")

    try:
        execute_from_command_line(sys.argv)
    except Exception as e:
        print(f"\n❌ Ошибка запуска Django: {e}")
        import traceback
        traceback.print_exc()
        input("\nНажмите Enter для выхода...")
        sys.exit(1)


if __name__ == "__main__":
    main()