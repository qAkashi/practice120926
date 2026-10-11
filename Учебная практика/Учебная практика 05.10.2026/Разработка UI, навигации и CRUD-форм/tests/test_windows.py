from datetime import date
import gc
import threading
import time
from unittest.mock import Mock

import psycopg
import pytest

from main_window import MainWindow
from partner_edit_window import PartnerEditWindow
from partner_history_window import PartnerHistoryWindow


def sample(partner_id=1):
    return {
        "partner_id": partner_id, "partner_name": f"ООО Партнёр {partner_id}", "partner_type": "ООО",
        "rating": 0, "address": "", "director_name": "", "phone": "", "email": f"p{partner_id}@example.ru",
        "inn": f"{partner_id:010d}", "total_quantity": 0, "discount_percent": 0,
    }


class FakeService:
    def __init__(self):
        self.partners = [sample(index) for index in range(1, 51)]
        self.error = None

    def call(self, operation, *arguments):
        if self.error is not None:
            raise self.error
        if operation.__name__ == "list_partners":
            return list(self.partners)
        if operation.__name__ == "get_partner":
            return next(dict(item) for item in self.partners if item["partner_id"] == arguments[0])
        if operation.__name__ == "get_history":
            return dict(self.partners[0]), [("Товар", date(2026, 10, 5), 2)]
        if operation.__name__ == "save_partner":
            values, partner_id = arguments
            if partner_id is None:
                partner_id = 51
                self.partners.append(sample(partner_id))
            partner = next(item for item in self.partners if item["partner_id"] == partner_id)
            partner.update(values)
            return partner_id
        return None


def wait_for(root, condition):
    deadline = time.monotonic() + 4
    while not condition():
        root.update()
        if time.monotonic() > deadline:
            raise AssertionError("Операция UI не завершилась")
        time.sleep(0.01)
    root.update()


@pytest.fixture
def window(monkeypatch):
    gc.collect()
    monkeypatch.setattr("tkinter.messagebox.showerror", Mock())
    monkeypatch.setattr("tkinter.messagebox.showinfo", Mock())
    monkeypatch.setattr("tkinter.messagebox.askyesno", Mock(return_value=True))
    root = MainWindow(FakeService(), auto_connect=False)
    root.withdraw()
    root.partners = list(root.service.partners)
    root.render_partners()
    root.update()
    yield root
    if root.child is not None:
        if isinstance(root.child, PartnerEditWindow):
            root.child.set_busy(False)
            root.child.close(saved=True)
        else:
            root.child.close()
    if not root.closed:
        root.close()
    gc.collect()


def test_titles_logo_icon_and_form_fields(window):
    assert "Реестр" in window.title()
    assert window.logo_image.width() > 0
    window.add_partner()
    card = window.child
    assert "Добавление" in card.title()
    assert str(card.entries["partner_type"]["state"]) == "readonly"
    assert len(card.entries) == 8
    assert card.values["partner_name"].get() == ""
    assert card.values["rating"].get() == "0"


@pytest.mark.parametrize(("value", "allowed"), [
    ("", True), ("0", True), ("123", True), ("-1", False), ("1.2", False),
    ("a", False), ("2147483648", False), ("١", False),
])
def test_rating_input_filter(value, allowed):
    assert PartnerEditWindow.rating_allowed(value) == allowed


def test_back_preserves_search_selection_and_scroll(window):
    window.search.set("Партнёр")
    window.tree.selection_set("20")
    window.tree.yview_moveto(0.4)
    before = window.tree.yview()[0]
    window.edit_partner()
    wait_for(window, lambda: window.child is not None)
    assert window.child.partner_id == 20
    assert "Редактирование" in window.child.title()
    window.child.close()
    assert window.search.get() == "Партнёр"
    assert window.selected_id() == 20
    assert window.tree.yview()[0] == before


def test_save_refreshes_table_and_closes_card(window):
    window.tree.selection_set("1")
    window.edit_partner()
    wait_for(window, lambda: window.child is not None)
    window.child.values["partner_name"].set("Новое имя")
    window.child.save()
    wait_for(window, lambda: window.child is None and not window.busy)
    assert window.tree.item("1", "values")[0] == "Новое имя"
    assert window.selected_id() == 1


def test_add_partner_refreshes_table(window):
    window.add_partner()
    card = window.child
    for key, value in sample(51).items():
        if key in card.values:
            card.values[key].set(str(value))
    card.save()
    wait_for(window, lambda: window.child is None and not window.busy)
    assert window.tree.exists("51")
    assert window.selected_id() == 51


def test_invalid_data_keeps_card_open(window):
    window.add_partner()
    card = window.child
    card.save()
    assert window.child is card
    assert not window.busy
    assert not card.closed


def test_placeholder_is_not_saved_as_input(window):
    window.add_partner()
    card = window.child
    assert card.values["email"].get() == ""
    assert card.entries["email"].placeholder["text"] == "Пример: partner@example.ru"
    card.values["email"].set("new@example.ru")
    assert not card.entries["email"].placeholder.place_info()


def test_failed_save_preserves_input_and_allows_retry(window):
    window.tree.selection_set("1")
    window.edit_partner()
    wait_for(window, lambda: window.child is not None)
    card = window.child
    card.values["partner_name"].set("Изменено")
    window.service.error = psycopg.OperationalError("offline")
    card.save()
    wait_for(window, lambda: not window.busy)
    assert window.child is card
    assert card.values["partner_name"].get() == "Изменено"
    assert not card.busy
    window.service.error = None
    card.save()
    wait_for(window, lambda: window.child is None and not window.busy)


def test_discard_can_be_cancelled(window, monkeypatch):
    window.add_partner()
    card = window.child
    card.values["partner_name"].set("Черновик")
    monkeypatch.setattr("tkinter.messagebox.askyesno", Mock(return_value=False))
    assert card.close() is False
    assert window.child is card
    assert card.values["partner_name"].get() == "Черновик"


def test_history_and_empty_state(window):
    window.tree.selection_set("1")
    window.show_history()
    wait_for(window, lambda: isinstance(window.child, PartnerHistoryWindow))
    history = window.child
    assert history.partner_id == 1
    assert history.tree.item("0", "values") == ("Товар", "05.10.2026", "2")
    assert "ООО Партнёр 1" in history.title()
    history.close()
    assert window.selected_id() == 1
    window.child = PartnerHistoryWindow(window, sample(), [])
    assert "пока нет продаж" in window.child.status.get()


def test_closing_during_loading_does_not_call_destroyed_widgets(window):
    release = threading.Event()
    service = window.service

    def slow_call(operation, *arguments):
        release.wait(2)
        return service.partners

    service.call = slow_call
    window.refresh()
    window.close()
    release.set()
    assert window.closed
