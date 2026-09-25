from pathlib import Path
import sys


practice_directory = Path(__file__).resolve().parent
navigation_directory = practice_directory / 'Проектирование многооконной архитектуры и навигации'
form_directory = practice_directory / 'Разработка формы добавления и редактирования партнера'
crud_directory = practice_directory / 'Интеграция формы с БД (CRUD-операции и обновление UI)'
ux_directory = practice_directory / 'Обработка исключений и интерактивные уведомления (UX и UI)'


def configure_imports():
    # Названия учебных папок содержат пробелы; модули импортируются из их путей.
    for directory in (navigation_directory, form_directory, crud_directory, ux_directory):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
