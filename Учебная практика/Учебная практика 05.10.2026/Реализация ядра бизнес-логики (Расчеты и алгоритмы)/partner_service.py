from discount import calculate_partner_discount


def get_partner_with_discount(connection, partner_id: int) -> dict | None:
    if type(partner_id) is not int or not 0 < partner_id <= 2147483647:
        raise ValueError("ID партнёра должен быть положительным целым числом.")

    row = connection.execute(
        """
        SELECT p.partner_id, p.partner_name, p.inn, p.email,
               COALESCE(SUM(s.quantity), 0) AS total_quantity
        FROM partners AS p
        LEFT JOIN sales_history AS s ON s.partner_id = p.partner_id
        WHERE p.partner_id = %s
        GROUP BY p.partner_id, p.partner_name, p.inn, p.email
        """,
        (partner_id,),
    ).fetchone()
    if row is None:
        return None
    return {
        "partner_id": row[0],
        "partner_name": row[1],
        "inn": row[2],
        "email": row[3],
        "total_quantity": row[4],
        "discount_percent": calculate_partner_discount(row[4]),
    }

