from decimal import Decimal
import inspect
from unittest.mock import Mock

import pytest

import material_reference_data
from material_calculator import calculate_material_quantity


@pytest.mark.parametrize("arguments, expected", [
    ((1, 1, 10, 2.0, 3.0), 95),
    ((2, 2, 4, 1.5, 2.5), 33),
    ((3, 3, 2, 2.0, 3.0), 12),
    ((3, 1, 1000, 1.0, 1.0), 1050),
    ((3, 3, 1, 0.07, 100.0), 7),
    ((3, 3, 1, 7.0000001, 1.0), 8),
    ((3, 3, 1, 0.00001, 0.00001), 1),
    ((3, 3, 1, 1e308, 1e308), 10 ** 616),
    ((1, 1, 10, 2, 3), 95),
])
def test_formula_and_exact_ceiling(arguments, expected):
    result = calculate_material_quantity(*arguments)
    assert result == expected
    assert type(result) is int


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("invalid", [0, -1, 1.5, True, "1", None])
def test_ids_and_quantity_require_positive_integers(position, invalid):
    arguments = [1, 1, 10, 2.0, 3.0]
    arguments[position] = invalid
    assert calculate_material_quantity(*arguments) == -1


@pytest.mark.parametrize("position", [3, 4])
@pytest.mark.parametrize("invalid", [0, -0.1, True, "2", None, float("nan"), float("inf"), float("-inf")])
def test_parameters_require_finite_positive_numbers(position, invalid):
    arguments = [1, 1, 10, 2.0, 3.0]
    arguments[position] = invalid
    assert calculate_material_quantity(*arguments) == -1


@pytest.mark.parametrize("product_type_id, material_type_id", [(999, 1), (1, 999), (999, 999)])
def test_unknown_reference_ids(product_type_id, material_type_id):
    assert calculate_material_quantity(product_type_id, material_type_id, 10, 2.0, 3.0) == -1


def test_coefficients_are_read_by_id_on_each_call(monkeypatch):
    product_lookup = Mock(side_effect=[Decimal("2.5"), Decimal("3")])
    material_lookup = Mock(side_effect=[Decimal("1.25"), Decimal("0")])
    monkeypatch.setattr(material_reference_data, "get_product_type_coefficient", product_lookup)
    monkeypatch.setattr(material_reference_data, "get_material_defect_percentage", material_lookup)
    assert calculate_material_quantity(42, 77, 10, 2.0, 3.0) == 152
    assert calculate_material_quantity(42, 77, 10, 2.0, 3.0) == 180
    assert product_lookup.call_count == 2
    assert material_lookup.call_count == 2
    product_lookup.assert_called_with(42)
    material_lookup.assert_called_with(77)


@pytest.mark.parametrize("coefficient, defect", [
    (0, 5), (-1, 5), (Decimal("NaN"), 5), (True, 5),
    (1, -0.1), (1, 100.01), (1, Decimal("Infinity")), (1, "5"),
])
def test_invalid_reference_values_return_minus_one(monkeypatch, coefficient, defect):
    monkeypatch.setattr(material_reference_data, "get_product_type_coefficient", lambda key: coefficient)
    monkeypatch.setattr(material_reference_data, "get_material_defect_percentage", lambda key: defect)
    assert calculate_material_quantity(1, 1, 10, 2.0, 3.0) == -1


def test_one_hundred_percent_means_double_reserve(monkeypatch):
    monkeypatch.setattr(material_reference_data, "get_material_defect_percentage", lambda key: Decimal("100"))
    assert calculate_material_quantity(3, 1, 10, 2.0, 3.0) == 120


def test_method_has_exactly_five_required_parameters():
    parameters = inspect.signature(calculate_material_quantity).parameters
    assert list(parameters) == ["product_type_id", "material_type_id", "quantity", "param_1", "param_2"]
    assert all(parameter.default is inspect.Parameter.empty for parameter in parameters.values())
