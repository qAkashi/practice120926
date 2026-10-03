from pathlib import Path
import sys


def find_module_directory(parent, directory_name, module_name):
    preferred = parent / directory_name
    if (preferred / module_name).is_file():
        return preferred
    # Папки заданий могут переименовываться; имя Python-модуля остаётся прежним.
    matches = list(parent.glob(f"*/{module_name}"))
    if len(matches) == 1:
        return matches[0].parent
    raise RuntimeError(
        f"Не удалось однозначно найти {module_name} в папке {parent}. "
        "Проверьте, что файл присутствует только в одной папке задания."
    )


practice_directory = Path(__file__).resolve().parent
previous_directory = practice_directory.parent / "Учебная практика 21.09.2026"
navigation_directory = previous_directory / "Проектирование многооконной архитектуры и навигации"
form_directory = previous_directory / "Разработка формы добавления и редактирования партнера"
crud_directory = previous_directory / "Интеграция формы с БД (CRUD-операции и обновление UI)"
ux_directory = previous_directory / "Обработка исключений и интерактивные уведомления (UX и UI)"
history_directory = find_module_directory(
    practice_directory, "Разработка интерфейса истории реализации продукции", "history_main_window.py",
)
materials_directory = find_module_directory(
    practice_directory, "Разработка ядра алгоритма расчета материалов", "material_calculator.py",
)
calculator_ui_directory = find_module_directory(
    practice_directory, "Модульное тестирование (Unit Testing) и аудит безопасности", "material_main_window.py",
)


def configure_imports():
    # Общие модули предыдущего этапа используются без изменения его версии.
    for directory in (navigation_directory, form_directory, crud_directory, ux_directory,
                      history_directory, materials_directory, calculator_ui_directory):
        if str(directory) not in sys.path:
            sys.path.insert(0, str(directory))
