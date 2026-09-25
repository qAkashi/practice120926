from typing import Any

import psycopg
from psycopg.rows import dict_row

from partner_discount import calculate_partner_discount
from partner_validation import PartnerNotFoundError, validate_partner


def read_partners(connection, partner_id=None) -> list[dict[str, Any]]:
    where_clause = "" if partner_id is None else "WHERE p.partner_id = %s"
    query = f"""
        SELECT p.partner_id, p.company_name, p.inn, p.contact_email,
               p.phone, p.rating, p.partner_type, p.address, p.director_name,
               COALESCE(SUM(di.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN deliveries AS d ON d.partner_id = p.partner_id
        LEFT JOIN delivery_items AS di ON di.delivery_id = d.delivery_id
        {where_clause}
        GROUP BY p.partner_id, p.company_name, p.inn, p.contact_email,
                 p.phone, p.rating, p.partner_type, p.address, p.director_name
        ORDER BY p.company_name, p.partner_id
    """
    parameters = () if partner_id is None else (partner_id,)
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, parameters)
        partners = cursor.fetchall()
    for partner in partners:
        partner["total_quantity"] = int(partner["total_quantity"] or 0)
        partner["discount_percent"] = calculate_partner_discount(partner["total_quantity"])
    return partners


def get_partners_with_discounts(connection: psycopg.Connection) -> list[dict[str, Any]]:
    return read_partners(connection)


def get_partner_with_discount(
    connection: psycopg.Connection,
    partner_id: int,
) -> dict[str, Any] | None:
    if type(partner_id) is not int or partner_id <= 0:
        raise ValueError("ID партнера должен быть положительным целым числом.")
    partners = read_partners(connection, partner_id)
    return partners[0] if partners else None


def save_partner(connection, values, partner_id=None):
    if partner_id is not None and (type(partner_id) is not int or partner_id <= 0):
        raise ValueError("ID партнёра должен быть положительным целым числом.")
    data = validate_partner(values)
    parameters = (
        data["company_name"], data["partner_type"], data["rating"], data["address"],
        data["director_name"], data["phone"], data["contact_email"], data["inn"],
    )
    with connection.transaction():
        with connection.cursor() as cursor:
            if partner_id is None:
                cursor.execute("""
                    INSERT INTO partners (
                        company_name, partner_type, rating, address,
                        director_name, phone, contact_email, inn
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING partner_id
                """, parameters)
            else:
                # Меняем только атрибуты: PK и связанные отгрузки не затрагиваются.
                cursor.execute("""
                    UPDATE partners
                    SET company_name = %s, partner_type = %s, rating = %s, address = %s,
                        director_name = %s, phone = %s, contact_email = %s, inn = %s
                    WHERE partner_id = %s
                    RETURNING partner_id
                """, parameters + (partner_id,))
            saved = cursor.fetchone()
            if saved is None:
                raise PartnerNotFoundError("Партнёр уже удалён. Изменения не сохранены.")
    return saved[0]
