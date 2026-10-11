import gc
import threading
import time
from unittest.mock import Mock

import psycopg
import pytest

from main_window import MainWindow
from partner_edit_window import PartnerEditWindow
from crm_validation import ValidationError
from ui_common import describe_error


def partner(index=1):
    return {
        "partner_id": index, "partner_name": f"Партнёр {index}", "partner_type": "ООО",
        "rating": 0, "address": "", "director_name": "", "phone": "",
        "email": f"p{index}@example.ru", "inn": f"{index:010d}",
        "total_quantity": 0, "discount_percent": 0,
    }


class Service:
    def __init__(self):
        self.calls = 0

    def call(self, operation, *arguments):
        self.calls += 1
        if operation.__name__ == "get_partner":
            return partner()
        return [partner()]


def wait_for(root, condition):
    deadline = time.monotonic() + 5
    while not condition():
        root.update()
        if time.monotonic() > deadline:
            raise AssertionError("UI не ответил")
        time.sleep(0.01)
    root.update()


@pytest.fixture
def window(monkeypatch):
    gc.collect()
    monkeypatch.setattr("tkinter.messagebox.showerror", Mock())
    monkeypatch.setattr("tkinter.messagebox.showinfo", Mock())
    monkeypatch.setattr("tkinter.messagebox.askyesno", Mock(return_value=True))
    root = MainWindow(Service(), auto_connect=False)
    root.withdraw()
    root.partners = [partner()]
    root.render_partners()
    root.update()
    yield root
    if root.child:
        if isinstance(root.child, PartnerEditWindow):
            root.child.set_busy(False)
            root.child.close(saved=True)
        else:
            root.child.close()
    if not root.closed:
        root.close()
    gc.collect()


@pytest.mark.parametrize("error", [
    ValidationError("rating", "Рейтинг должен быть целым неотрицательным числом."),
    psycopg.OperationalError("secret password"), psycopg.errors.UniqueViolation("private email"),
    psycopg.errors.UndefinedTable("private schema"), RuntimeError("private payload"),
    KeyError("private setting"), psycopg.errors.InsufficientPrivilege("private user"),
])
def test_error_messages_include_steps_without_private_details(error):
    message = describe_error(error)
    assert "1." in message
    assert "2." in message
    assert "private" not in message
    assert "secret" not in message


def test_invalid_form_uses_error_messagebox(window, monkeypatch):
    error_dialog = Mock()
    monkeypatch.setattr("tkinter.messagebox.showerror", error_dialog)
    window.add_partner()
    window.child.save()
    title, message = error_dialog.call_args.args
    assert title == "Ошибка ввода"
    assert "1." in message and "2." in message
    assert window.service.calls == 0


def test_discard_warning_and_cancel_preserve_values(window, monkeypatch):
    warning = Mock(return_value=False)
    monkeypatch.setattr("tkinter.messagebox.askyesno", warning)
    window.add_partner()
    window.child.values["partner_name"].set("Черновик")
    assert not window.child.close()
    assert warning.call_args.kwargs["icon"] == "warning"
    assert "без возможности восстановления" in warning.call_args.args[1]
    assert window.child.values["partner_name"].get() == "Черновик"
    warning.return_value = True
    assert window.child.close()
    assert window.child is None


def test_failed_callback_does_not_stop_polling(window, monkeypatch):
    error_dialog = Mock()
    monkeypatch.setattr("tkinter.messagebox.showerror", error_dialog)

    def broken(result):
        raise RuntimeError("private payload")

    window.submit(lambda connection: None, (), broken)
    wait_for(window, lambda: error_dialog.called)
    assert "private payload" not in error_dialog.call_args.args[1]
    window.refresh()
    wait_for(window, lambda: not window.busy)
    assert window.tree.exists("1")
    assert window.service.calls == 2


def test_unexpected_tk_callback_shows_error_and_app_remains_usable(window, monkeypatch):
    error_dialog = Mock()
    monkeypatch.setattr("tkinter.messagebox.showerror", error_dialog)

    def broken():
        raise RuntimeError("private")

    window.after(0, broken)
    wait_for(window, lambda: error_dialog.called)
    window.add_partner()
    assert window.child is not None


def test_failed_thread_start_unlocks_controls(window, monkeypatch):
    monkeypatch.setattr("threading.Thread.start", Mock(side_effect=RuntimeError("cannot start")))
    window.refresh()
    assert not window.busy
    assert str(window.refresh_button["state"]) == "normal"


def test_double_clicks_only_start_one_request(window):
    release = threading.Event()
    original = window.service.call

    def blocked(operation, *arguments):
        release.wait(4)
        return original(operation, *arguments)

    window.service.call = blocked
    window.tree.selection_set("1")
    window.edit_partner()
    for index in range(100):
        window.edit_partner()
        window.show_history()
        window.refresh()
    release.set()
    wait_for(window, lambda: window.child is not None)
    assert window.service.calls == 1


def test_search_treats_sql_as_text_without_query(window):
    window.search.set("' OR 1=1; DROP TABLE partners; --")
    assert not window.tree.get_children()
    assert window.service.calls == 0
    window.search.set("")
    assert window.tree.exists("1")


def test_large_list_and_repeated_search(window):
    window.partners = [partner(index) for index in range(1, 10001)]
    window.render_partners()
    assert len(window.tree.get_children()) == 10000
    for index in range(20):
        window.search.set("Партнёр 9999")
        assert window.tree.get_children() == ("9999",)
        window.search.set("нет совпадений")
        assert not window.tree.get_children()
    window.search.set("")
    assert len(window.tree.get_children()) == 10000
    assert window.service.calls == 0

