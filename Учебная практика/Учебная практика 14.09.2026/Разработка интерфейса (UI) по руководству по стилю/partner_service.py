from typing import Any

import psycopg
from psycopg.rows import dict_row

from partner_discount import calculate_partner_discount


def get_partners_with_discounts(connection: psycopg.Connection) -> list[dict[str, Any]]:
   
    query = """
        SELECT p.partner_id, p.company_name, p.inn, p.contact_email,
               p.phone, p.rating, COALESCE(SUM(di.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN deliveries AS d ON d.partner_id = p.partner_id
        LEFT JOIN delivery_items AS di ON di.delivery_id = d.delivery_id
        GROUP BY p.partner_id, p.company_name, p.inn, p.contact_email,
                 p.phone, p.rating
        ORDER BY p.company_name, p.partner_id
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query)
        partners = cursor.fetchall()
    for partner in partners:
        partner["discount_percent"] = calculate_partner_discount(
            partner["total_quantity"]
        )
    return partners
