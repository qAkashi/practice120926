from decimal import Decimal
from types import MappingProxyType


# Учебные мок-данные: в исходной БД справочников типов продукции и материалов пока нет.
product_type_coefficients = MappingProxyType({
    1: Decimal("1.5"),
    2: Decimal("2.0"),
    3: Decimal("1.0"),
})

material_defect_percentages = MappingProxyType({
    1: Decimal("5.0"),
    2: Decimal("10.0"),
    3: Decimal("0.0"),
})


def get_product_type_coefficient(product_type_id: int) -> Decimal | None:
    return product_type_coefficients.get(product_type_id)


def get_material_defect_percentage(material_type_id: int) -> Decimal | None:
    return material_defect_percentages.get(material_type_id)
