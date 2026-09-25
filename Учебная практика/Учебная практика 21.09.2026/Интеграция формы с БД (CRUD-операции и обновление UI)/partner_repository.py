from database import connect_database
from partner_service import get_partner_with_discount, get_partners_with_discounts, save_partner
from partner_validation import PartnerNotFoundError


def load_partners(password):
    with connect_database(password) as connection:
        return get_partners_with_discounts(connection)


def load_partner(password, partner_id):
    with connect_database(password) as connection:
        partner = get_partner_with_discount(connection, partner_id)
    if partner is None:
        raise PartnerNotFoundError("Партнёр уже удалён. Обновите список.")
    return partner


def store_partner(password, values, partner_id=None):
    # Возврат в интерфейс происходит только после успешного COMMIT.
    with connect_database(password) as connection:
        saved_id = save_partner(connection, values, partner_id)
    return saved_id
