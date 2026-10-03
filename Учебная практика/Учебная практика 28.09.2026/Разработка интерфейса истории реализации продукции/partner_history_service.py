from psycopg.rows import dict_row

from database import connect_database
from partner_validation import PartnerNotFoundError


def get_partner_history(connection, partner_id):
    if type(partner_id) is not int or partner_id <= 0:
        raise ValueError("ID партнёра должен быть положительным целым числом.")
    # LEFT JOIN с партнёром отличает пустую историю от удалённой карточки.
    query = """
        WITH history AS (
            SELECT d.partner_id, d.delivery_id, di.line_number,
                   pr.product_name, di.quantity, d.delivery_date
            FROM deliveries AS d
            JOIN delivery_items AS di ON di.delivery_id = d.delivery_id
            JOIN products AS pr ON pr.product_id = di.product_id
            WHERE d.partner_id = %s
        )
        SELECT p.partner_id, p.company_name, p.partner_type,
               h.delivery_id, h.line_number, h.product_name, h.quantity, h.delivery_date
        FROM partners AS p
        LEFT JOIN history AS h ON h.partner_id = p.partner_id
        WHERE p.partner_id = %s
        ORDER BY h.delivery_date DESC, h.delivery_id DESC, h.line_number
    """
    with connection.cursor(row_factory=dict_row) as cursor:
        cursor.execute(query, (partner_id, partner_id))
        records = cursor.fetchall()
    if not records:
        raise PartnerNotFoundError("Партнёр не найден. Вернитесь в реестр, нажмите «Обновить» и выберите партнёра заново.")
    partner = records[0]
    return {
        "partner_id": partner["partner_id"],
        "company_name": partner["company_name"],
        "partner_type": partner["partner_type"],
        "rows": [
            {key: row[key] for key in ("delivery_id", "line_number", "product_name", "quantity", "delivery_date")}
            for row in records if row["delivery_id"] is not None
        ],
    }


def load_partner_history(password, partner_id):
    with connect_database(password) as connection:
        return get_partner_history(connection, partner_id)
