import pytest

from material_calculator import calculate_material_quantity


def test_standard_calculation():
    assert calculate_material_quantity(2, 2, 4, 1.5, 2.5) == 33


def test_fractional_consumption_is_rounded_up():
    assert calculate_material_quantity(1, 1, 10, 2.0, 3.0) == 95


@pytest.mark.parametrize("product_type_id, material_type_id", [(999, 1), (1, 999)])
def test_unknown_type_returns_minus_one(product_type_id, material_type_id):
    assert calculate_material_quantity(product_type_id, material_type_id, 10, 2.0, 3.0) == -1


@pytest.mark.parametrize("param_1, param_2", [(-2.0, 3.0), (2.0, -3.0)])
def test_negative_parameter_returns_minus_one(param_1, param_2):
    assert calculate_material_quantity(1, 1, 10, param_1, param_2) == -1


@pytest.mark.parametrize("quantity", [0, -1])
def test_nonpositive_quantity_returns_minus_one(quantity):
    assert calculate_material_quantity(1, 1, quantity, 2.0, 3.0) == -1
