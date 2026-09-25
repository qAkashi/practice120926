import threading
import tkinter as tk

import psycopg
import pytest

from conftest import wait_until, widget_texts
from partner_service import get_partners_with_discounts


def test_auto_load_no_history_email_and_zero_discount(connection, make_app):
    application = make_app(
        lambda password: get_partners_with_discounts(connection),
        initial_password="test",
    )
    wait_until(application, lambda: len(application.cards) == 2)
    texts = widget_texts(application.cards_frame)
    assert texts.count("0%") == 2
    assert texts.count("Куплено за весь период: 0 шт.") == 2
    assert "Email: first@example.invalid" in texts
    assert "Телефон: не указан" in texts
    assert application.root.title() == "CRM: Список партнеров и скидок"
    assert application.icon_image.width() > 0
    assert application.logo_image.width() > 0


def test_startup_opens_login_and_cancel_is_safe(make_app):
    application = make_app(lambda password: [])
    wait_until(application, lambda: application.login_dialog is not None)
    assert application.login_dialog.winfo_exists()
    application.login_dialog.destroy()
    application.root.update()
    assert not application.closed
    assert not application.loading
    assert application.password is None


def test_submit_password_loads_without_extra_button(connection, make_app):
    application = make_app(lambda password: get_partners_with_discounts(connection))
    wait_until(application, lambda: application.login_dialog is not None)
    entry = next(w for w in application.login_dialog.winfo_children() if isinstance(w, tk.Entry))
    entry.insert(0, "test")
    buttons_frame = next(w for w in application.login_dialog.winfo_children() if isinstance(w, tk.Frame))
    submit = next(w for w in buttons_frame.winfo_children() if w.cget("text") == "Войти")
    submit.invoke()
    wait_until(application, lambda: len(application.cards) == 2)
    assert "Данные из БД" in application.status.get()


def test_refresh_recalculates_discount_from_database(connection, make_app):
    connection.execute("INSERT INTO deliveries VALUES (10, 1, '2026-01-01')")
    connection.execute("INSERT INTO delivery_items VALUES (10, 1, 9999)")
    application = make_app(
        lambda password: get_partners_with_discounts(connection),
        initial_password="test",
    )
    wait_until(application, lambda: len(application.cards) == 2)
    connection.execute("UPDATE delivery_items SET quantity = 10000")
    application.refresh()
    wait_until(application, lambda: not application.loading)
    assert "5%" in widget_texts(application.cards_frame)
    assert "Куплено за весь период: 10000 шт." in widget_texts(application.cards_frame)


def test_search_and_empty_results(connection, make_app):
    application = make_app(
        lambda password: get_partners_with_discounts(connection),
        initial_password="test",
    )
    wait_until(application, lambda: len(application.cards) == 2)
    application.search_text.set("ПЕРВЫЙ")
    assert len(application.cards) == 1
    application.search_text.set("не существует")
    assert len(application.cards) == 0
    assert "Показано: 0 из 2" in application.status.get()


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (psycopg.OperationalError("offline"), "Не удалось подключиться"),
        (psycopg.errors.InvalidPassword("bad password"), "Неверный пароль"),
        (psycopg.errors.UndefinedTable("missing"), "нет нужных таблиц"),
        (psycopg.errors.QueryCanceled("timeout"), "слишком много времени"),
        (FileNotFoundError("config"), "database.ini"),
        (psycopg.errors.InsufficientPrivilege("denied"), "права пользователя"),
        (RuntimeError("unexpected"), "Не удалось загрузить данные"),
    ],
    ids=["offline", "password", "missing_tables", "timeout", "config", "permissions", "unexpected"],
)
def test_failure_is_visible_and_retry_works(make_app, error, expected):
    def failing_loader(password):
        raise error

    application = make_app(failing_loader, initial_password="test")
    wait_until(application, lambda: application.password is None)
    assert expected in " ".join(widget_texts(application.cards_frame))
    assert str(application.refresh_button.cget("state")) == "normal"
    application.load_partners = lambda password: []
    application.password = "retry"
    application.refresh()
    wait_until(application, lambda: not application.loading)
    assert "В базе пока нет партнеров." in widget_texts(application.cards_frame)


def test_unavailable_real_server_is_handled(make_app):
    def unavailable_loader(password):
        with psycopg.connect(host="127.0.0.1", port=1, dbname="postgres", connect_timeout=2):
            return []

    application = make_app(unavailable_loader, initial_password="test")
    wait_until(application, lambda: application.password is None)
    assert "Не удалось подключиться" in " ".join(widget_texts(application.cards_frame))


def test_slow_load_does_not_freeze_window_and_close_is_safe(make_app):
    release = threading.Event()
    completed = threading.Event()

    def slow_loader(password):
        release.wait(5)
        completed.set()
        return []

    application = make_app(slow_loader, initial_password="test")
    wait_until(application, lambda: application.loading)
    tick = []
    application.root.after(10, lambda: tick.append(True))
    wait_until(application, lambda: bool(tick))
    application.close()
    release.set()
    assert completed.wait(2)
