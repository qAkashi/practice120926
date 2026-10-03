from datetime import date
import threading

import psycopg
import pytest

import partner_history_service
from conftest import wait_until
from partner_history_service import get_partner_history, load_partner_history
from partner_history_window import PartnerHistoryWindow
from partner_service import save_partner
from partner_validation import PartnerNotFoundError
from test_partner_crud import crud_database, partner_values


def history_result(partner_id=1, rows=None):
    return {
        "partner_id": partner_id, "company_name": "Актуальное название", "partner_type": "ООО",
        "rows": [] if rows is None else rows,
    }


def history_row(name="Мыло", quantity=25, sold_on=date(2026, 3, 15)):
    return {"delivery_id": 101, "line_number": 1, "product_name": name,
            "quantity": quantity, "delivery_date": sold_on}


def populated_app(make_app, loader):
    application = make_app(lambda password: [], initial_password="session", auto_start=False,
                           read_history=loader)
    application.partners = [
        {"partner_id": key, "company_name": f"Партнёр {key}", "discount_percent": 0,
         "total_quantity": 0, "phone": None, "rating": 0}
        for key in (1, 2)
    ]
    application.render_partners()
    return application


def test_join_returns_only_selected_partner_with_all_lines_and_dates(crud_database, partner_values, monkeypatch):
    connection, connect, _ = crud_database
    first = save_partner(connection, partner_values)
    second = save_partner(connection, partner_values | {"inn": "9876543210", "contact_email": "second@example.ru"})
    connection.execute("INSERT INTO products (product_id, product_name) VALUES (1, 'Мыло'), (2, 'Порошок')")
    connection.execute("""
        INSERT INTO deliveries (delivery_id, partner_id, delivery_date)
        VALUES (10, %s, '2025-01-01'), (11, %s, '2026-10-01'), (12, %s, '2026-10-02')
    """, (first, first, second))
    connection.execute("""
        INSERT INTO delivery_items VALUES
        (10, 1, 1, 7, 100), (11, 1, 1, 2, 100), (11, 2, 2, 3, 200), (12, 1, 2, 9999, 200)
    """)
    monkeypatch.setattr(partner_history_service, "connect_database", lambda password: connect())
    history = load_partner_history("", first)
    assert history["partner_id"] == first
    assert history["company_name"] == partner_values["company_name"]
    assert [(row["product_name"], row["quantity"]) for row in history["rows"]] == [("Мыло", 2), ("Порошок", 3), ("Мыло", 7)]
    assert [row["delivery_date"] for row in history["rows"]] == [date(2026, 10, 1), date(2026, 10, 1), date(2025, 1, 1)]


def test_no_sales_and_empty_delivery_return_empty_history(crud_database, partner_values):
    connection, _, _ = crud_database
    partner_id = save_partner(connection, partner_values)
    assert get_partner_history(connection, partner_id)["rows"] == []
    connection.execute("INSERT INTO deliveries (partner_id, delivery_date) VALUES (%s, '2026-01-01')", (partner_id,))
    assert get_partner_history(connection, partner_id)["rows"] == []


def test_unknown_partner_is_distinguished_from_no_sales(crud_database):
    connection, _, _ = crud_database
    with pytest.raises(PartnerNotFoundError):
        get_partner_history(connection, 999)


@pytest.mark.parametrize("partner_id", [0, -1, True, "1 OR 1=1", 1.5])
def test_bad_id_is_rejected_before_sql(partner_id):
    with pytest.raises(ValueError):
        get_partner_history(None, partner_id)


def test_click_selection_passes_id_and_displays_product_quantity_date(make_app):
    requested = []

    def load(password, partner_id):
        requested.append((password, partner_id))
        return history_result(partner_id, [history_row()])

    application = populated_app(make_app, load)
    assert str(application.history_button.cget("state")) == "disabled"
    application.root.deiconify()
    application.root.update()
    card = application.partner_cards[2][0]
    card.winfo_children()[0].event_generate("<Button-1>")
    assert application.selected_partner_id == 2
    assert str(application.history_button.cget("state")) == "normal"
    assert card.cget("highlightthickness") == 2
    application.history_button.invoke()
    window = application.history_window
    assert isinstance(window, PartnerHistoryWindow)
    assert window.partner_id == 2
    wait_until(application, lambda: not window.loading)
    assert requested == [("session", 2)]
    assert window.title() == "CRM: История реализации продукции — ООО Актуальное название"
    assert window.logo_image is application.logo_image
    assert window.icon_image is application.icon_image
    assert [window.table.heading(key)["text"] for key in ("product", "quantity", "date")] == [
        "Наименование продукции", "Количество (шт.)", "Дата продажи",
    ]
    item = window.table.get_children()[0]
    assert window.table.item(item, "values") == ("Мыло", "25", "15.03.2026")


def test_history_without_sales_has_explanation(make_app):
    application = populated_app(make_app, lambda password, partner_id: history_result(partner_id))
    application.select_partner(1)
    application.history_button.invoke()
    window = application.history_window
    wait_until(application, lambda: not window.loading)
    assert not window.table.get_children()
    assert "нет отгрузок" in window.status.get()


def test_footer_buttons_remain_visible_in_small_window(make_app):
    application = populated_app(make_app, lambda password, partner_id: history_result(partner_id))
    application.root.deiconify()
    application.select_partner(1)
    application.history_button.invoke()
    window = application.history_window
    window.geometry("660x420")
    wait_until(application, lambda: not window.loading)
    for button in (window.back_button, window.refresh_button):
        assert button.winfo_ismapped()
        assert button.winfo_rooty() >= window.winfo_rooty()
        assert button.winfo_rooty() + button.winfo_height() <= window.winfo_rooty() + window.winfo_height()
    assert window.table.winfo_height() > 50


@pytest.mark.parametrize("action", ["back", "escape", "cross"])
def test_return_keeps_main_search_selection_and_scroll(make_app, action):
    application = populated_app(make_app, lambda password, partner_id: history_result(partner_id))
    application.search_text.set("Партнёр")
    application.root.update()
    application.select_partner(1)
    cards = list(application.cards)
    scroll = application.canvas.yview()
    application.history_button.invoke()
    window = application.history_window
    actions = {"back": window.back_button.invoke, "escape": window.on_escape,
               "cross": lambda: window.tk.call(window.protocol("WM_DELETE_WINDOW"))}
    actions[action]()
    assert application.history_window is None
    assert application.search_text.get() == "Партнёр"
    assert application.selected_partner_id == 1
    assert application.cards == cards
    assert application.canvas.yview() == scroll
    assert application.root.grab_current() is None


def test_filter_removes_hidden_selection_and_disables_history(make_app):
    application = populated_app(make_app, lambda password, partner_id: history_result(partner_id))
    application.select_partner(1)
    application.search_text.set("Партнёр 2")
    assert application.selected_partner_id is None
    assert str(application.history_button.cget("state")) == "disabled"
    application.open_partner_history()
    assert application.history_window is None


def test_history_is_single_window_and_blocks_other_navigation(make_app):
    application = populated_app(make_app, lambda password, partner_id: history_result(partner_id))
    application.select_partner(1)
    application.open_partner_history()
    window = application.history_window
    application.open_partner_history()
    application.open_partner_editor()
    application.connect()
    application.refresh()
    assert application.history_window is window
    assert application.edit_window is None
    assert not application.loading
    application.close()
    assert not window.winfo_exists()


def test_failed_history_can_retry_and_long_names_are_scrollable(make_app, message_boxes):
    attempts = []
    product_name = "Очень длинное наименование продукции " * 10

    def load(password, partner_id):
        attempts.append(partner_id)
        if len(attempts) == 1:
            raise psycopg.OperationalError("offline")
        return history_result(partner_id, [history_row(product_name)])

    application = populated_app(make_app, load)
    application.select_partner(1)
    application.open_partner_history()
    window = application.history_window
    wait_until(application, lambda: not window.loading)
    assert message_boxes["error"].call_args.kwargs["title"] == "Ошибка загрузки истории"
    assert not window.table.get_children()
    window.refresh_button.invoke()
    wait_until(application, lambda: not window.loading)
    assert len(window.table.get_children()) == 1
    assert window.table.column("product")["width"] > 460


def test_closing_during_background_load_is_safe(make_app):
    release = threading.Event()
    finished = threading.Event()

    def load(password, partner_id):
        release.wait(5)
        finished.set()
        return history_result(partner_id)

    application = populated_app(make_app, load)
    application.select_partner(1)
    application.open_partner_history()
    window = application.history_window
    assert window.loading
    window.close()
    release.set()
    wait_until(application, finished.is_set)
    assert not window.winfo_exists()
    assert application.history_window is None
