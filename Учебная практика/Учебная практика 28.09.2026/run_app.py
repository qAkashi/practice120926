import os
import tkinter as tk

from project_paths import configure_imports


def run():
    configure_imports()
    from app_logging import configure_logging, log_error
    from audit_main_window import MainWindow
    from partner_repository import load_partners

    configure_logging()
    try:
        root = tk.Tk()
        MainWindow(root, load_partners, initial_password=os.environ.get("PGPASSWORD"))
        root.mainloop()
    except Exception as error:
        log_error("Запуск приложения", error, "Не удалось запустить приложение. Проверьте файлы проекта и окружение Python.")
        raise


if __name__ == "__main__":
    run()
