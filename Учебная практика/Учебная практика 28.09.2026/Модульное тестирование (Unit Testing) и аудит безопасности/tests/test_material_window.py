from unittest.mock import Mock

import pytest

from material_ui_fixtures import calculator_app


def fill_valid(window):
    values = {"product_type_id": "1", "material_type_id": "1", "quantity": "10", "param_1": "2", "param_2": "3"}
    for key, value in values.items():
        window.values[key].set(value)


def open_calculator(application):
    application.material_button.invoke()
    window = application.material_window
    fill_valid(window)
    return window


def test_real_calculation_title_and_shared_style(calculator_app):
    application, errors = calculator_app
    window = open_calculator(application)
    window.calculate_button.invoke()
    assert window.result_text.get() == "Необходимое количество сырья: 95"
    assert window.title() == "CRM: Расчёт сырья для производства"
    assert window.logo_image is application.logo_image
    assert window.icon_image is application.icon_image
    assert window.cget("bg") == application.root.cget("bg")
    errors.assert_not_called()


@pytest.mark.parametrize("key, value", [
    ("quantity", "0"), ("quantity", "-5"), ("quantity", "1.5"), ("quantity", ""),
    ("quantity", "abc"), ("product_type_id", "999"), ("material_type_id", "999"),
    ("product_type_id", "-1"), ("material_type_id", "0"), ("product_type_id", "abc"),
    ("param_1", "-2"), ("param_2", "-3"), ("param_1", "0"), ("param_2", ""),
    ("param_1", "NaN"), ("param_2", "inf"), ("param_1", "-inf"), ("param_2", "1e9999"),
])
def test_bad_input_shows_error_and_can_be_corrected(calculator_app, key, value):
    application, errors = calculator_app
    window = open_calculator(application)
    window.calculate_button.invoke()
    window.values[key].set(value)
    assert "95" not in window.result_text.get()
    window.calculate_button.invoke()
    errors.assert_called_once()
    dialog = errors.call_args.kwargs
    assert dialog["title"] == "Ошибка расчёта сырья"
    assert dialog["icon"] == "error"
    assert dialog["parent"] is window
    assert "Исправьте значения" in dialog["message"]
    assert window.values[key].get() == value
    assert window.winfo_exists()
    assert window.result_text.get() == "Расчёт не выполнен."
    fill_valid(window)
    window.calculate_button.invoke()
    assert window.result_text.get().endswith("95")
    assert str(window.calculate_button.cget("state")) == "normal"


def test_returned_minus_one_is_handled_without_showing_it_as_consumption(calculator_app):
    application, errors = calculator_app
    window = open_calculator(application)
    window.calculator = Mock(return_value=-1)
    window.calculate_button.invoke()
    window.calculator.assert_called_once_with(1, 1, 10, 2.0, 3.0)
    assert "-1" not in window.result_text.get()
    errors.assert_called_once()


def test_comma_spaces_and_enter(calculator_app):
    application, errors = calculator_app
    window = open_calculator(application)
    window.values["param_1"].set(" 2,5 ")
    assert window.on_calculate() == "break"
    assert window.result_text.get().endswith("119")
    errors.assert_not_called()


def test_editing_after_success_invalidates_previous_result(calculator_app):
    application, errors = calculator_app
    window = open_calculator(application)
    window.calculate_button.invoke()
    window.values["quantity"].set("20")
    assert window.result_text.get() == "Параметры изменены. Нажмите «Рассчитать»."
    window.calculate_button.invoke()
    assert window.result_text.get().endswith("189")
    errors.assert_not_called()


@pytest.mark.parametrize("action", ["back", "escape", "cross"])
def test_return_preserves_main_state_and_releases_grab(calculator_app, action):
    application, _ = calculator_app
    application.partners = [{"partner_id": 1, "company_name": "Партнёр", "discount_percent": 0,
                             "total_quantity": 0, "rating": 0, "phone": None}]
    application.search_text.set("Партнёр")
    application.select_partner(1)
    cards = list(application.cards)
    scroll = application.canvas.yview()
    window = open_calculator(application)
    actions = {"back": window.back_button.invoke, "escape": window.on_escape,
               "cross": lambda: window.tk.call(window.protocol("WM_DELETE_WINDOW"))}
    actions[action]()
    assert application.material_window is None
    assert application.root.grab_current() is None
    assert application.search_text.get() == "Партнёр"
    assert application.selected_partner_id == 1
    assert application.cards == cards
    assert application.canvas.yview() == scroll


def test_single_window_blocks_other_modals_and_closes_with_main(calculator_app):
    application, _ = calculator_app
    window = open_calculator(application)
    application.open_material_calculator()
    assert application.material_window is window
    application.open_partner_editor()
    application.open_partner_history()
    application.connect()
    application.refresh()
    assert application.edit_window is None
    assert application.history_window is None
    assert application.login_dialog is None
    assert not application.loading
    application.close()
    assert window.closed
    window.calculate()
    window.close()


def test_can_calculate_without_database_login(calculator_app):
    application, errors = calculator_app
    application.password = None
    window = open_calculator(application)
    window.calculate_button.invoke()
    assert window.result_text.get().endswith("95")
    errors.assert_not_called()


def test_calculator_does_not_take_grab_from_partner_editor(calculator_app):
    application, _ = calculator_app
    application.open_partner_editor()
    editor = application.edit_window
    application.open_material_calculator()
    assert application.material_window is None
    assert application.root.grab_current() is editor


def test_controls_and_result_visible_at_minimum_size(calculator_app):
    application, _ = calculator_app
    application.root.deiconify()
    window = open_calculator(application)
    window.geometry("680x650")
    window.calculate_button.invoke()
    application.root.update()
    for widget in [*window.entries.values(), window.result_label, window.calculate_button, window.back_button]:
        assert widget.winfo_ismapped()
        assert widget.winfo_rooty() + widget.winfo_height() <= window.winfo_rooty() + window.winfo_height()
        assert widget.winfo_rootx() + widget.winfo_width() <= window.winfo_rootx() + window.winfo_width()
    assert window.result_label.winfo_height() >= 50
