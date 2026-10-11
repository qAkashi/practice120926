from contextlib import nullcontext
from decimal import Decimal
from unittest.mock import MagicMock

import psycopg
import pytest

from discount import calculate_partner_discount
from material_calculator import MaterialCalculator
from partner_service import get_partner_with_discount


@pytest.mark.parametrize(("quantity", "expected"), [
    (0, 0), (9999, 0), (10000, 5), (49999, 5), (50000, 10),
    (299999, 10), (300000, 15), (1000000, 15),
])
def test_discount_boundaries(quantity, expected):
    assert calculate_partner_discount(quantity) == expected


@pytest.mark.parametrize("quantity", [-1, 1.5, True, None, "10000"])
def test_discount_rejects_invalid_quantity(quantity):
    with pytest.raises(ValueError):
        calculate_partner_discount(quantity)


@pytest.fixture
def connection():
    connection = MagicMock()
    connection.transaction.side_effect = nullcontext
    connection.execute.return_value.fetchone.return_value = (Decimal("1.5"), Decimal("5"))
    return connection


def test_material_standard_calculation_and_bound_parameters(connection):
    assert MaterialCalculator(connection).calculate_materials(1, 2, 10, 2.0, 3.0) == 95
    query, parameters = connection.execute.call_args.args
    assert parameters == (1, 2)
    assert query.count("%s") == 2


@pytest.mark.parametrize(("coefficient", "defect", "quantity", "first", "second", "expected"), [
    ("1", "0", 1, 0.1, 0.2, 1),
    ("1", "0", 1, 10.0, 10.0, 100),
    ("1", "0", 100, 0.1, 0.1, 1),
    ("1.5", "5", 10, 2.0, 3.0, 95),
    ("1", "100", 1, 2.0, 3.0, 12),
])
def test_rounding_and_defect(connection, coefficient, defect, quantity, first, second, expected):
    connection.execute.return_value.fetchone.return_value = (Decimal(coefficient), Decimal(defect))
    assert MaterialCalculator(connection).calculate_materials(1, 1, quantity, first, second) == expected


@pytest.mark.parametrize("arguments", [
    (-1, 1, 10, 2, 3), (1, 0, 10, 2, 3), (True, 1, 10, 2, 3),
    ("1 OR 1=1", 1, 10, 2, 3), (1, 2147483648, 10, 2, 3),
    (1, 1, 0, 2, 3), (1, 1, -1, 2, 3), (1, 1, 1.5, 2, 3),
    (1, 1, True, 2, 3), (1, 1, 10, -2, 3), (1, 1, 10, 2, -3),
    (1, 1, 10, 0, 3), (1, 1, 10, 2, 0), (1, 1, 10, float("nan"), 3),
    (1, 1, 10, 2, float("inf")), (1, 1, 10, None, 3),
    (1, 1, 10, "2", 3), (1, 1, 10, True, 3),
])
def test_invalid_parameters_return_minus_one_without_query(connection, arguments):
    assert MaterialCalculator(connection).calculate_materials(*arguments) == -1
    connection.execute.assert_not_called()


def test_missing_type_returns_minus_one(connection):
    connection.execute.return_value.fetchone.return_value = None
    assert MaterialCalculator(connection).calculate_materials(999, 1, 10, 2, 3) == -1


@pytest.mark.parametrize("row", [
    (0, 5), (-1, 5), (1, -1), (1, 101), (None, 5), (float("inf"), 5),
])
def test_invalid_reference_values_return_minus_one(connection, row):
    connection.execute.return_value.fetchone.return_value = row
    assert MaterialCalculator(connection).calculate_materials(1, 1, 10, 2, 3) == -1


def test_database_failure_returns_minus_one_without_exposing_details(connection, caplog):
    connection.execute.side_effect = psycopg.OperationalError("private connection details")
    assert MaterialCalculator(connection).calculate_materials(1, 1, 10, 2, 3) == -1
    assert "OperationalError" in caplog.text
    assert "private connection details" not in caplog.text


@pytest.mark.parametrize(("quantity", "discount"), [(0, 0), (10000, 5), (50000, 10), (300000, 15)])
def test_partner_discount_uses_aggregate(connection, quantity, discount):
    connection.execute.return_value.fetchone.return_value = (1, "Партнёр", "1234567890", "a@example.ru", quantity)
    partner = get_partner_with_discount(connection, 1)
    assert partner["total_quantity"] == quantity
    assert partner["discount_percent"] == discount
    query, parameters = connection.execute.call_args.args
    assert parameters == (1,)
    assert "LEFT JOIN" in query
    assert "COALESCE(SUM(s.quantity), 0)" in query


def test_partner_not_found(connection):
    connection.execute.return_value.fetchone.return_value = None
    assert get_partner_with_discount(connection, 999) is None


@pytest.mark.parametrize("partner_id", [-1, 0, True, "1 OR 1=1", 2147483648])
def test_invalid_partner_id(connection, partner_id):
    with pytest.raises(ValueError):
        get_partner_with_discount(connection, partner_id)
    connection.execute.assert_not_called()

