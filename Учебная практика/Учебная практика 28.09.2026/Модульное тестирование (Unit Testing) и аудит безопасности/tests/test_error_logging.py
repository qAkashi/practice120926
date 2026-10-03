from concurrent.futures import ThreadPoolExecutor
import re
from unittest.mock import Mock

import psycopg
import pytest

from app_logging import configure_logging, log_error, logged_operation, log_validation
from audit_fixtures import audited_app, log_file
from errors import get_error_message


def test_error_has_datetime_level_type_and_readable_message(log_file):
    log_error("Расчёт сырья", ValueError("secret input"), "Неверный формат числа.")
    line = log_file.read_text(encoding="utf-8")
    assert re.match(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} \| ERROR \|", line)
    assert "Расчёт сырья | ValueError | Неверный формат числа." in line
    assert "secret input" not in line


def test_worker_exception_is_logged_and_reraised_without_secrets(log_file):
    secret = "private_password_123"
    error = psycopg.OperationalError(f"password={secret} personal@example.ru")
    callback = Mock(side_effect=error)
    wrapped = logged_operation("Загрузка партнёров", callback, get_error_message)
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(wrapped, secret)
        with pytest.raises(psycopg.OperationalError) as raised:
            future.result()
    assert raised.value is error
    text = log_file.read_text(encoding="utf-8")
    assert "OperationalError" in text
    assert "PostgreSQL" in text
    assert secret not in text
    assert "personal@example.ru" not in text


def test_successful_operation_does_not_log_error(log_file):
    callback = Mock(return_value=42)
    assert logged_operation("Проверка", callback, str)(1, key=2) == 42
    callback.assert_called_once_with(1, key=2)
    assert log_file.read_text(encoding="utf-8") == ""


def test_reconfiguration_does_not_duplicate_records(log_file):
    configure_logging(log_file)
    configure_logging(log_file)
    log_validation("Проверка", "Некорректные данные.\nПовторите ввод.")
    assert len(log_file.read_text(encoding="utf-8").splitlines()) == 1


def test_unwritable_log_falls_back_to_console(log_file, tmp_path, capsys):
    configure_logging(tmp_path / "missing_directory" / "app.log")
    log_error("Проверка", ValueError(), "Неверное число.")
    output = capsys.readouterr().err
    assert "ошибки выводятся в консоль" in output
    assert "Неверное число" in output


def prepare_calculator(application):
    application.open_material_calculator()
    window = application.material_window
    for key, value in {"product_type_id": "1", "material_type_id": "1", "quantity": "10", "param_1": "2", "param_2": "3"}.items():
        window.values[key].set(value)
    return window


@pytest.mark.parametrize("value, expected", [("abc", "ValueError"), ("-2", "Метод вернул -1")])
def test_bad_calculator_input_is_logged_and_shown(audited_app, value, expected):
    application, errors, _, path = audited_app
    window = prepare_calculator(application)
    window.values["param_1"].set(value)
    window.calculate_button.invoke()
    assert expected in path.read_text(encoding="utf-8")
    errors.assert_called_once()
    assert window.winfo_exists()


def test_unexpected_calculator_error_is_logged_without_crash(audited_app):
    application, errors, _, path = audited_app
    window = prepare_calculator(application)
    window.calculator = Mock(side_effect=RuntimeError("private text"))
    window.calculate_button.invoke()
    text = path.read_text(encoding="utf-8")
    assert "RuntimeError" in text
    assert "private text" not in text
    assert "app.log" in errors.call_args.kwargs["message"]


def test_partner_validation_is_logged(audited_app):
    application, errors, _, path = audited_app
    application.open_partner_editor()
    application.edit_window.save_button.invoke()
    assert "Проверка карточки" in path.read_text(encoding="utf-8")
    errors.assert_called_once()


def test_tk_callback_exception_is_logged_and_reported(audited_app):
    application, errors, _, path = audited_app
    application.root.report_callback_exception(RuntimeError, RuntimeError("secret"), None)
    text = path.read_text(encoding="utf-8")
    assert "Обработчик интерфейса | RuntimeError" in text
    assert "secret" not in text
    errors.assert_called_once()


def test_all_database_operations_are_wrapped(audited_app):
    application, _, _, path = audited_app
    for operation in (application.load_partners, application.read_partner,
                      application.write_partner, application.read_history):
        assert hasattr(operation, "__wrapped__")
    assert path.read_text(encoding="utf-8") == ""
