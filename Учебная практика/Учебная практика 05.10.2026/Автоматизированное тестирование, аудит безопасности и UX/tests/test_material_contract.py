from contextlib import nullcontext
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
import psycopg

from material_calculator import MaterialCalculator


@pytest.fixture
def connection():
    connection = MagicMock()
    connection.transaction.side_effect = nullcontext
    connection.execute.return_value.fetchone.return_value = (Decimal("1.5"), Decimal("5"))
    return connection


def test_standard_calculation(connection):
    assert MaterialCalculator(connection).calculate_materials(1, 1, 10, 2, 3) == 95


def test_rounds_fraction_strictly_up(connection):
    connection.execute.return_value.fetchone.return_value = (Decimal("1"), Decimal("0"))
    assert MaterialCalculator(connection).calculate_materials(1, 1, 1, 1.01, 1) == 2


def test_exact_integer_is_not_rounded_to_next_integer(connection):
    connection.execute.return_value.fetchone.return_value = (Decimal("1"), Decimal("0"))
    assert MaterialCalculator(connection).calculate_materials(1, 1, 100, 0.1, 0.1) == 1


@pytest.mark.parametrize("identifiers", [(999, 1), (1, 999)])
def test_unknown_type_returns_minus_one(connection, identifiers):
    connection.execute.return_value.fetchone.return_value = None
    assert MaterialCalculator(connection).calculate_materials(*identifiers, 10, 2, 3) == -1


@pytest.mark.parametrize("parameters", [(-2, 3), (2, -3), (0, 3), (2, 0)])
def test_invalid_dimensions_return_minus_one(connection, parameters):
    assert MaterialCalculator(connection).calculate_materials(1, 1, 10, *parameters) == -1
    connection.execute.assert_not_called()


@pytest.mark.parametrize("quantity", [0, -1, 1.5, True])
def test_invalid_quantity_returns_minus_one(connection, quantity):
    assert MaterialCalculator(connection).calculate_materials(1, 1, quantity, 2, 3) == -1


def test_unavailable_database_returns_minus_one(connection):
    connection.execute.side_effect = psycopg.OperationalError("offline")
    assert MaterialCalculator(connection).calculate_materials(1, 1, 10, 2, 3) == -1


def test_repeated_calculations_are_stable(connection):
    calculator = MaterialCalculator(connection)
    for index in range(1000):
        assert calculator.calculate_materials(1, 1, 10, 2, 3) == 95
    assert connection.execute.call_count == 1000

