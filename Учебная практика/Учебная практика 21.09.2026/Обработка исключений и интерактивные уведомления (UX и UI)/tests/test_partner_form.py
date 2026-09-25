from decimal import Decimal
from tkinter import ttk

import pytest

from conftest import wait_until
from partner_edit_window import prepare_form_values


def test_type_can_only_be_selected_from_list(make_app):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    combo = application.edit_window.entries["partner_type"]
    assert isinstance(combo, ttk.Combobox)
    assert str(combo.cget("state")) == "readonly"
    assert {"ЗАО", "ООО", "ИП"}.issubset(combo.cget("values"))
    combo.insert(0, "Произвольный тип")
    assert combo.get() == ""
    combo.current(1)
    assert application.edit_window.values["partner_type"].get() == "ООО"


@pytest.mark.parametrize("value", ["0", "1", "10", "300000"])
def test_rating_accepts_nonnegative_integers(make_app, value):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    entry = application.edit_window.entries["rating"]
    entry.delete(0, "end")
    entry.insert(0, value)
    assert entry.get() == value


@pytest.mark.parametrize("value", ["-1", "4.8", "4,8", "abc", " 1", "²", "١"])
def test_rating_keeps_input_for_validation_on_save(make_app, value):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    entry = application.edit_window.entries["rating"]
    entry.delete(0, "end")
    entry.insert(0, value)
    assert entry.get() == value
    entry.delete(0, "end")
    entry.insert(0, "10")
    assert entry.get() == "10"


def test_old_fractional_rating_is_not_rounded(make_app):
    application = make_app(lambda password: [], auto_start=False)
    partner = {"partner_id": 1, "company_name": "ООО Пример", "rating": Decimal("4.8")}
    application.read_partner = lambda password, partner_id: dict(partner)
    application.open_partner_editor(partner)
    wait_until(application, lambda: application.edit_window is not None)
    editor = application.edit_window
    assert editor.values["rating"].get() == ""
    assert "В базе: 4.8" in editor.rating_hint
    assert editor.values["company_name"].get() == "Пример"
    assert editor.values["partner_type"].get() == "ООО"
    assert partner["rating"] == Decimal("4.8")
    editor.close()
    application.open_partner_editor(partner)
    wait_until(application, lambda: application.edit_window is not None)
    assert "В базе: 4.8" in application.edit_window.rating_hint


def test_explicit_type_and_name_are_preserved():
    values, hint = prepare_form_values({
        "partner_type": "ИП", "company_name": "ООО в названии", "rating": None,
    })
    assert values["partner_type"] == "ИП"
    assert values["company_name"] == "ООО в названии"
    assert values["rating"] is None


def test_cancel_discards_all_fields_and_reopens_empty_form(make_app):
    application = make_app(lambda password: [], auto_start=False)
    application.open_partner_editor()
    editor = application.edit_window
    draft = {
        "company_name": "Пример",
        "partner_type": "ЗАО",
        "rating": "10",
        "address": "Москва, ул. Примерная, д. 1",
        "director_name": "Иванов Иван Иванович",
        "phone": "+7 (999) 123-45-67",
        "contact_email": "partner@example.ru",
        "inn": "1234567890",
    }
    assert editor.values.keys() == draft.keys()
    for key, value in draft.items():
        editor.values[key].set(value)
    editor.close()
    application.open_partner_editor()
    actual = {key: value.get() for key, value in application.edit_window.values.items()}
    assert actual == dict.fromkeys(draft, "") | {"rating": "0"}


def test_tooltips_show_hints_and_close_with_editor(make_app):
    application = make_app(lambda password: [], auto_start=False)
    application.root.deiconify()
    application.open_partner_editor()
    editor = application.edit_window
    application.root.update()
    for key, example in (("phone", "+7 (999) 123-45-67"), ("contact_email", "partner@example.ru")):
        tooltip = editor.tooltips[key]
        assert example in tooltip.text
        editor.entries[key].event_generate("<Enter>")
        application.root.update()
        assert tooltip.window is not None
        editor.entries[key].event_generate("<Leave>")
        assert tooltip.window is None
    editor.tooltips["phone"].show()
    editor.close()
    application.root.update()
    assert all(tooltip.window is None for tooltip in editor.tooltips.values())
    assert application.root.grab_current() is None
