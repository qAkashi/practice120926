import threading
from decimal import Decimal

import psycopg
import pytest

from conftest import wait_until


valid_values = {
    "company_name": "Пример", "partner_type": "ООО", "rating": "10",
    "address": "Москва", "director_name": "Иванов Иван Иванович",
    "phone": "+79991234567", "contact_email": "office@example.ru", "inn": "1234567890",
}


def fill(editor, values):
    for key, value in values.items():
        editor.values[key].set(value)


@pytest.mark.parametrize("field,value", [
    ("company_name", ""), ("company_name", "   "),
    ("contact_email", ""), ("contact_email", " \t "),
    ("rating", "-1"), ("rating", "4.8"), ("rating", "4,8"),
    ("rating", "abc"), ("rating", ""),
])
def test_invalid_input_shows_error_without_sending_to_database(make_app, message_boxes, field, value):
    calls = []
    application = make_app(lambda password: [], initial_password="", auto_start=False,
                           write_partner=lambda *args: calls.append(args))
    application.open_partner_editor()
    editor = application.edit_window
    fill(editor, valid_values | {field: value})
    editor.save_button.invoke()
    options = message_boxes["error"].call_args.kwargs
    assert options["title"] == "Ошибка ввода"
    assert options["icon"] == "error"
    assert options["parent"] is editor
    assert "введите" in options["message"].lower()
    assert not calls
    assert not editor.busy
    assert editor.values[field].get() == value
    assert not message_boxes["information"].called


@pytest.mark.parametrize("close_action", ["button", "escape", "cross", "main"])
def test_cancel_warning_preserves_data_and_yes_discards(make_app, message_boxes, close_action):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    editor = application.edit_window
    editor.values["company_name"].set("Не потерять")
    actions = {
        "button": editor.back_button.invoke,
        "escape": editor.on_escape,
        "cross": lambda: editor.tk.call(editor.protocol("WM_DELETE_WINDOW")),
        "main": application.close,
    }
    message_boxes["warning"].return_value = False
    actions[close_action]()
    options = message_boxes["warning"].call_args.kwargs
    assert options["title"] == "Несохранённые изменения"
    assert options["icon"] == "warning"
    assert options["default"] == "no"
    assert options["parent"] is editor
    assert "безвозвратно" in options["message"]
    assert "«Нет»" in options["message"]
    assert editor.winfo_exists()
    assert editor.values["company_name"].get() == "Не потерять"
    assert not application.closed
    message_boxes["warning"].return_value = True
    actions[close_action]()
    assert not editor.winfo_exists()
    assert application.closed == (close_action == "main")


def test_untouched_or_reverted_form_has_no_warning(make_app, message_boxes):
    application = make_app(lambda password: [], auto_start=False)
    for changed in (False, True):
        application.open_partner_editor()
        editor = application.edit_window
        if changed:
            editor.values["company_name"].set("Временная правка")
            editor.values["company_name"].set("")
        editor.close()
    assert not message_boxes["warning"].called


def test_loaded_values_are_not_unsaved_changes(make_app, message_boxes):
    partner = valid_values | {"partner_id": 7, "rating": Decimal("4.8")}
    application = make_app(lambda password: [], auto_start=False,
                           read_partner=lambda password, partner_id: partner)
    application.open_partner_editor({"partner_id": 7})
    wait_until(application, lambda: application.edit_window is not None)
    assert not application.edit_window.has_changes()
    application.edit_window.close()
    assert not message_boxes["warning"].called


@pytest.mark.parametrize("editing", [False, True])
def test_information_only_after_save_completes(make_app, message_boxes, editing):
    release = threading.Event()

    def store(password, values, partner_id):
        release.wait(5)
        return 7

    application = make_app(lambda password: [], initial_password="", auto_start=False,
                           write_partner=store,
                           read_partner=lambda password, partner_id: valid_values | {"partner_id": 7})
    application.open_partner_editor({"partner_id": 7} if editing else None)
    wait_until(application, lambda: application.edit_window is not None)
    fill(application.edit_window, valid_values | {"company_name": "Новое имя"})
    application.edit_window.save_button.invoke()
    try:
        assert application.edit_window.busy
        assert not message_boxes["information"].called
    finally:
        release.set()
    wait_until(application, lambda: application.edit_window is None and not application.loading)
    message_boxes["information"].assert_called_once()
    options = message_boxes["information"].call_args.kwargs
    assert options["icon"] == "info"
    assert options["parent"] is application.root
    assert options["title"] == ("Изменения сохранены" if editing else "Партнёр добавлен")
    assert "7" in options["message"]
    assert not message_boxes["warning"].called


@pytest.mark.parametrize("operation", ["list", "read", "save"])
def test_database_failure_shows_actionable_error(make_app, message_boxes, operation):
    def fail(*args):
        raise psycopg.OperationalError("technical credentials must not be shown")

    application = make_app(fail, initial_password="", auto_start=False,
                           read_partner=fail, write_partner=fail)
    if operation == "list":
        application.refresh()
    elif operation == "read":
        application.open_partner_editor({"partner_id": 7})
    else:
        application.open_partner_editor()
        fill(application.edit_window, valid_values)
        application.edit_window.save_button.invoke()
    wait_until(application, lambda: message_boxes["error"].called)
    options = message_boxes["error"].call_args.kwargs
    assert options["icon"] == "error"
    assert "Ошибка" in options["title"]
    assert "1." in options["message"] and "2." in options["message"]
    assert "technical credentials" not in options["message"]
    assert not message_boxes["information"].called
    if operation == "save":
        assert application.edit_window.values["company_name"].get() == valid_values["company_name"]
        assert not application.edit_window.busy
