from decimal import Decimal
import threading

import pytest

from conftest import wait_until
from main_window import MainWindow
from partner_edit_window import PartnerEditWindow


def test_add_button_opens_form_and_back_keeps_main_alive(make_app):
    application = make_app(lambda password: [], auto_start=False)
    assert isinstance(application, MainWindow)
    application.add_partner_button.invoke()
    editor = application.edit_window
    assert isinstance(editor, PartnerEditWindow)
    assert editor.title() == "CRM: Карточка партнера [Добавление]"
    assert application.root.title() == "CRM: Реестр партнеров"
    assert editor.values["rating"].get() == "0"
    assert all(value.get() == "" for key, value in editor.values.items() if key != "rating")
    editor.back_button.invoke()
    assert not editor.winfo_exists()
    assert application.edit_window is None
    assert application.root.winfo_exists()
    assert not application.closed


@pytest.mark.parametrize("close_method", ["button", "escape", "window_cross"])
def test_all_return_actions_allow_reopening_empty_form(make_app, close_method):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    editor = application.edit_window
    editor.values["company_name"].set("Новый партнер")
    editor.values["contact_email"].set("draft@example.invalid")
    if close_method == "button":
        editor.back_button.invoke()
    elif close_method == "escape":
        editor.on_escape()
    else:
        editor.tk.call(editor.protocol("WM_DELETE_WINDOW"))
    assert application.edit_window is None
    assert application.root.grab_current() is None
    application.open_partner_editor()
    assert application.edit_window.values["company_name"].get() == ""
    assert application.edit_window.values["contact_email"].get() == ""


def test_edit_form_prefills_values_without_mutating_partner(make_app):
    application = make_app(lambda password: [], auto_start=False)
    partner = {
        "partner_id": 7,
        "company_name": "ООО Партнер",
        "inn": "1234567890",
        "contact_email": "contact@example.invalid",
        "phone": None,
        "rating": Decimal("0.0"),
    }
    application.read_partner = lambda password, partner_id: dict(partner)
    application.open_partner_editor(partner)
    wait_until(application, lambda: application.edit_window is not None)
    editor = application.edit_window
    assert editor.title() == "CRM: Карточка партнера [Редактирование]"
    assert editor.values["inn"].get() == "1234567890"
    assert editor.values["phone"].get() == ""
    assert editor.values["rating"].get() == "0"
    editor.values["company_name"].set("Черновик изменения")
    editor.close()
    assert partner["company_name"] == "ООО Партнер"
    application.open_partner_editor(partner)
    wait_until(application, lambda: application.edit_window is not None)
    assert application.edit_window.values["company_name"].get() == "Партнер"
    application.edit_window.close()
    application.open_partner_editor()
    assert application.edit_window.values["company_name"].get() == ""


def test_navigation_preserves_search_scroll_cards_and_connection(make_app):
    application = make_app(lambda password: [], initial_password="session", auto_start=False)
    application.root.deiconify()
    application.partners = [
        {"partner_id": number, "company_name": f"Партнер {number}", "phone": None,
         "rating": None, "contact_email": "test@example.invalid",
         "total_quantity": 0, "discount_percent": 0}
        for number in range(20)
    ]
    application.search_text.set("Партнер")
    application.root.update()
    application.canvas.yview_moveto(0.5)
    application.root.update()
    before_scroll = application.canvas.yview()
    before_cards = list(application.cards)
    before_status = application.status.get()
    before_partners = application.partners
    application.open_partner_editor()
    application.refresh()
    application.edit_window.back_button.invoke()
    application.root.update()
    assert application.search_text.get() == "Партнер"
    assert application.canvas.yview() == pytest.approx(before_scroll)
    assert application.cards == before_cards
    assert application.partners is before_partners
    assert application.status.get() == before_status
    assert application.password == "session"


def test_repeated_open_does_not_duplicate_editor(make_app):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    first_editor = application.edit_window
    application.open_partner_editor()
    assert application.edit_window is first_editor
    assert sum(isinstance(w, PartnerEditWindow) for w in application.root.winfo_children()) == 1


def test_closing_main_also_closes_editor(make_app):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    editor = application.edit_window
    application.close()
    assert application.closed
    assert not editor.winfo_exists()
    application.close()


def test_editor_is_not_opened_during_loading(make_app):
    release = threading.Event()

    def loader(password):
        release.wait(3)
        return []

    application = make_app(loader, initial_password="session")
    wait_until(application, lambda: application.loading)
    try:
        application.add_partner_button.invoke()
        application.open_partner_editor()
        assert application.edit_window is None
        assert str(application.add_partner_button.cget("state")) == "disabled"
    finally:
        release.set()
    wait_until(application, lambda: not application.loading)
    assert str(application.add_partner_button.cget("state")) == "normal"
