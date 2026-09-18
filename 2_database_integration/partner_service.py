from typing import Any

import psycopg
from psycopg.rows import dict_row

from partner_discount import calculate_partner_discount


def get_partner_with_discount(
    connection: psycopg.Connection,
    partner_id: int,
) -> dict[str, Any] | None:  

    if type(partner_id) is not int or partner_id <= 0:
        raise ValueError("ID партнера должен быть положительным целым числом.")

    query = """
        SELECT
            p.partner_id,
            p.company_name,
            p.inn,
            p.contact_email,
            p.phone,
            p.rating,
            COALESCE(SUM(di.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN deliveries AS d ON d.partner_id = p.partner_id
        LEFT JOIN delivery_items AS di ON di.delivery_id = d.delivery_id
        WHERE p.partner_id = %s
        GROUP BY
            p.partner_id,
            p.company_name,
            p.inn,
            p.contact_email,
            p.phone,
            p.rating
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, (partner_id,))
        partner = cursor.fetchone()

    if partner is None:
        return None

    partner["discount_percent"] = calculate_partner_discount(
        partner["total_quantity"]
    )
    return partner
