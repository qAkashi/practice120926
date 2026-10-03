from app_logging import log_error, logged_operation, log_validation
from dialogs import show_error
from errors import get_error_message, get_partner_error_message
from material_main_window import MainWindow as MaterialMainWindow
from partner_history_service import load_partner_history
from partner_repository import load_partner, store_partner


class MainWindow(MaterialMainWindow):
    def __init__(self, root, load_partners, *args, **kwargs):
        operations = (
            ("read_partner", "Чтение карточки", load_partner),
            ("write_partner", "Сохранение карточки", store_partner),
            ("read_history", "Загрузка истории", load_partner_history),
        )
        for key, title, default in operations:
            callback = kwargs.get(key, default)
            kwargs[key] = logged_operation(title, callback, get_partner_error_message)
        loader = logged_operation("Загрузка партнёров", load_partners, get_error_message)
        super().__init__(root, loader, *args, **kwargs)
        self.root.report_callback_exception = self.report_callback_exception

    def show_partner_editor(self, partner=None):
        super().show_partner_editor(partner)
        show_form_error = self.edit_window.show_error

        def report_form_error(title, message):
            if title == "Ошибка ввода":
                log_validation("Проверка карточки", message)
            show_form_error(title, message)

        self.edit_window.show_error = report_form_error

    def report_callback_exception(self, exception_type, error, traceback):
        log_error("Обработчик интерфейса", error, "Не удалось выполнить действие в интерфейсе.")
        if not self.closed:
            show_error(self.root, "Ошибка приложения",
                       "Действие не выполнено. Повторите попытку. Если ошибка повторяется, "
                       "перезапустите приложение и передайте журнал app.log для проверки.")
