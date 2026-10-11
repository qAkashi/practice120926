from decimal import Decimal
from fractions import Fraction
import logging
from math import ceil

import psycopg


logger = logging.getLogger(__name__)


def as_fraction(value):
    if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
        raise ValueError("Ожидается конечное число.")
    return Fraction(str(value))


class MaterialCalculator:
    def __init__(self, connection):
        self.connection = connection

    def calculate_materials(
        self,
        product_type_id: int,
        material_type_id: int,
        quantity: int,
        param_1: float,
        param_2: float,
    ) -> int:
        identifiers = (product_type_id, material_type_id)
        if any(type(value) is not int or not 0 < value <= 2147483647 for value in identifiers):
            return -1
        if type(quantity) is not int or quantity <= 0:
            return -1
        try:
            first_parameter = as_fraction(param_1)
            second_parameter = as_fraction(param_2)
            if first_parameter <= 0 or second_parameter <= 0:
                return -1

            # В открытой транзакции psycopg создаёт savepoint для изоляции ошибки запроса.
            with self.connection.transaction():
                row = self.connection.execute(
                    """
                    SELECT p.coefficient, m.defect_percent
                    FROM product_types AS p
                    CROSS JOIN material_types AS m
                    WHERE p.product_type_id = %s AND m.material_type_id = %s
                    """,
                    (product_type_id, material_type_id),
                ).fetchone()
            if row is None:
                return -1
            coefficient = as_fraction(row[0])
            defect_percent = as_fraction(row[1])
            if coefficient <= 0 or not 0 <= defect_percent <= 100:
                return -1

            # Точные дроби исключают лишнюю единицу при ceil из-за погрешности float.
            net_consumption = first_parameter * second_parameter * coefficient * quantity
            return ceil(net_consumption * (1 + defect_percent / 100))
        except (ValueError, TypeError, OverflowError, ZeroDivisionError):
            return -1
        except psycopg.Error as error:
            logger.error("Справочники недоступны: %s", type(error).__name__)
            return -1

