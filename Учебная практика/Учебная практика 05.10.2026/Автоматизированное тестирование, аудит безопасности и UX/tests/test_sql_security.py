import ast
from contextlib import nullcontext
from unittest.mock import MagicMock

import pytest

from audit_paths import business_directory, ui_directory
from crm_repository import get_history, get_partner, save_partner
from material_calculator import MaterialCalculator


def make_connection():
    connection = MagicMock()
    connection.transaction.side_effect = nullcontext
    return connection


@pytest.mark.parametrize("partner_id", ["1 OR 1=1", "1; DROP TABLE partners; --"])
def test_partner_id_is_bound_as_parameter(partner_id):
    connection = make_connection()
    connection.execute.return_value.fetchone.return_value = (1, "Name", "ООО", 0, "", "", "", "a@b.ru", "1234567890")
    get_partner(connection, partner_id)
    query, values = connection.execute.call_args.args
    assert partner_id not in query
    assert values == (partner_id,)
    get_history(connection, partner_id)
    query, values = connection.execute.call_args.args
    assert partner_id not in query
    assert values == (partner_id,)


@pytest.mark.parametrize("partner_id", [None, 7])
def test_card_payload_is_bound_on_insert_and_update(partner_id):
    connection = make_connection()
    connection.execute.return_value.fetchone.return_value = (7,)
    payload = "O'Brien'); DROP TABLE partners; --"
    values = {
        "partner_name": payload, "partner_type": "ООО", "rating": "0",
        "address": payload, "director_name": payload, "phone": "",
        "email": "a@example.ru", "inn": "1234567890",
    }
    assert save_partner(connection, values, partner_id) == 7
    query, parameters = connection.execute.call_args.args
    assert payload not in query
    assert payload in parameters
    assert query.count("%s") == len(parameters)


def test_calculator_rejects_sql_text_before_query():
    connection = make_connection()
    assert MaterialCalculator(connection).calculate_materials("1 OR 1=1", 1, 10, 2, 3) == -1
    connection.execute.assert_not_called()


def test_application_queries_have_literal_templates_and_bound_values():
    paths = [
        ui_directory / "crm_repository.py",
        business_directory / "material_calculator.py",
        business_directory / "partner_service.py",
    ]
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr != "execute":
                continue
            argument = node.args[0]
            if isinstance(argument, ast.Call) and isinstance(argument.func, ast.Attribute):
                assert argument.func.attr == "read_text"
                continue
            assert isinstance(argument, ast.Constant) and isinstance(argument.value, str)
            if "%s" in argument.value:
                assert len(node.args) == 2

