from pathlib import Path

from project_paths import configure_paths

configure_paths()

from discount import calculate_partner_discount
from crm_validation import validate_partner


partner_columns = (
    "partner_id", "partner_name", "partner_type", "rating", "address",
    "director_name", "phone", "email", "inn",
)


class PartnerNotFoundError(ValueError):
    pass


def migrate(connection):
    with connection.transaction():
        connection.execute(Path(__file__).with_name("migration.sql").read_text(encoding="utf-8"))


def list_partners(connection):
    rows = connection.execute(
        """
        SELECT p.partner_id, p.partner_name, p.partner_type, p.rating, p.address,
               p.director_name, p.phone, p.email, p.inn, COALESCE(SUM(s.quantity), 0)
        FROM partners AS p
        LEFT JOIN sales_history AS s ON s.partner_id = p.partner_id
        GROUP BY p.partner_id
        ORDER BY lower(p.partner_name), p.partner_id
        """
    ).fetchall()
    partners = []
    for row in rows:
        partner = dict(zip(partner_columns, row[:9]))
        partner["total_quantity"] = row[9]
        partner["discount_percent"] = calculate_partner_discount(row[9])
        partners.append(partner)
    return partners


def get_partner(connection, partner_id):
    row = connection.execute(
        """
        SELECT partner_id, partner_name, partner_type, rating, address,
               director_name, phone, email, inn
        FROM partners WHERE partner_id = %s
        """,
        (partner_id,),
    ).fetchone()
    if row is None:
        raise PartnerNotFoundError("Партнёр больше не существует. Обновите список и выберите другую запись.")
    return dict(zip(partner_columns, row))


def save_partner(connection, values, partner_id=None):
    data = validate_partner(values)
    arguments = tuple(data[field] for field in partner_columns[1:])
    with connection.transaction():
        if partner_id is None:
            row = connection.execute(
                """
                INSERT INTO partners
                    (partner_name, partner_type, rating, address, director_name, phone, email, inn)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING partner_id
                """,
                arguments,
            ).fetchone()
        else:
            row = connection.execute(
                """
                UPDATE partners
                SET partner_name = %s, partner_type = %s, rating = %s, address = %s,
                    director_name = %s, phone = %s, email = %s, inn = %s
                WHERE partner_id = %s
                RETURNING partner_id
                """,
                (*arguments, partner_id),
            ).fetchone()
        if row is None:
            raise PartnerNotFoundError("Запись удалена другим пользователем. Вернитесь назад и обновите список.")
    return row[0]


def get_history(connection, partner_id):
    with connection.transaction():
        partner = get_partner(connection, partner_id)
        rows = connection.execute(
            """
            SELECT pr.product_name, s.sale_date, s.quantity
            FROM sales_history AS s
            JOIN products AS pr ON pr.product_id = s.product_id
            WHERE s.partner_id = %s
            ORDER BY s.sale_date DESC, s.sale_id DESC
            """,
            (partner_id,),
        ).fetchall()
    return partner, rows

