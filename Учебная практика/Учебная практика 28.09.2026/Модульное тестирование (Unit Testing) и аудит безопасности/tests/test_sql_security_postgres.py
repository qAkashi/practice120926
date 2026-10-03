import os

import pytest

from partner_service import get_partner_with_discount, save_partner
from test_partner_crud import crud_database, partner_values


pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_DSN"), reason="Нужно тестовое подключение PostgreSQL.")


@pytest.mark.parametrize("field", ["company_name", "address", "director_name"])
def test_insert_and_update_preserve_sql_payload_as_data(crud_database, partner_values, field):
    connection, _, _ = crud_database
    other = save_partner(connection, partner_values | {"inn": "9876543210", "contact_email": "other@example.ru"})
    payload = "x'); DROP TABLE partners CASCADE; --"
    partner_id = save_partner(connection, partner_values | {field: payload})
    assert get_partner_with_discount(connection, partner_id)[field] == payload
    assert connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 2
    changed_payload = "x' OR 1=1 --"
    save_partner(connection, partner_values | {field: changed_payload}, partner_id)
    assert get_partner_with_discount(connection, partner_id)[field] == changed_payload
    assert get_partner_with_discount(connection, other)[field] == partner_values[field]
    assert connection.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0] == 0
