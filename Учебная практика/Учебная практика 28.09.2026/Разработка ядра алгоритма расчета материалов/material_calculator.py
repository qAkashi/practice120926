from decimal import Decimal
from fractions import Fraction
from math import ceil

import material_reference_data


def as_fraction(value) -> Fraction | None:
    if type(value) not in (int, float, Decimal):
        return None
    try:
        # Десятичное представление исключает лишнюю единицу при ceil(0.07 * 100).
        return Fraction(str(value))
    except ValueError:
        return None


def calculate_material_quantity(
    product_type_id: int,
    material_type_id: int,
    quantity: int,
    param_1: float,
    param_2: float,
) -> int:
    """Вернуть расход сырья с запасом на брак; при неверных данных вернуть -1."""
    if any(type(value) is not int or value <= 0 for value in (product_type_id, material_type_id, quantity)):
        return -1

    first_parameter = as_fraction(param_1)
    second_parameter = as_fraction(param_2)
    if first_parameter is None or second_parameter is None:
        return -1
    if first_parameter <= 0 or second_parameter <= 0:
        return -1

    coefficient = as_fraction(material_reference_data.get_product_type_coefficient(product_type_id))
    defect_percentage = as_fraction(material_reference_data.get_material_defect_percentage(material_type_id))
    if coefficient is None or defect_percentage is None:
        return -1
    if coefficient <= 0 or not 0 <= defect_percentage <= 100:
        return -1

    base_consumption = first_parameter * second_parameter * coefficient
    net_consumption = base_consumption * quantity
    total_consumption = net_consumption * (1 + defect_percentage / 100)
    return ceil(total_consumption)
