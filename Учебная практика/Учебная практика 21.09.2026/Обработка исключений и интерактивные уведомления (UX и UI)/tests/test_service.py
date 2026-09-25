from unittest.mock import MagicMock

import pytest

from partner_service import get_partner_with_discount, get_partners_with_discounts


def test_no_sales_returns_zero(connection):
    partner = get_partner_with_discount(connection, 1)
    assert partner["total_quantity"] == 0
    assert partner["discount_percent"] == 0
    assert partner["contact_email"] == "first@example.invalid"


def test_empty_delivery_returns_zero(connection):
    connection.execute("INSERT INTO deliveries VALUES (10, 1, '2026-01-01')")
    assert get_partner_with_discount(connection, 1)["discount_percent"] == 0


@pytest.mark.parametrize("quantity", [None, 0])
def test_null_or_zero_quantity_in_history(connection, quantity):
    connection.execute("INSERT INTO deliveries VALUES (10, 1, '2026-01-01')")
    connection.execute("INSERT INTO delivery_items VALUES (10, 1, %s)", (quantity,))
    partner = get_partner_with_discount(connection, 1)
    assert partner["total_quantity"] == 0
    assert partner["discount_percent"] == 0


def test_python_normalizes_null_from_data_layer():
    connection = MagicMock()
    cursor = connection.cursor.return_value.__enter__.return_value
    cursor.fetchall.return_value = [{"partner_id": 1, "total_quantity": None}]
    partner = get_partners_with_discounts(connection)[0]
    assert partner["total_quantity"] == 0
    assert partner["discount_percent"] == 0


def test_all_periods_and_items_are_summed_without_other_partner(connection):
    connection.execute("""
        INSERT INTO deliveries VALUES
            (10, 1, '2020-01-01'), (11, 1, '2026-09-01'), (12, 2, '2026-09-01')
    """)
    connection.execute("""
        INSERT INTO delivery_items VALUES
            (10, 1, 4000), (10, 2, 4000), (11, 1, 2000), (12, 1, 300000)
    """)
    partners = {p["partner_id"]: p for p in get_partners_with_discounts(connection)}
    assert partners[1]["total_quantity"] == 10000
    assert partners[1]["discount_percent"] == 5
    assert partners[2]["discount_percent"] == 15


def test_list_includes_no_sales_and_is_sorted(connection):
    partners = get_partners_with_discounts(connection)
    assert [p["partner_id"] for p in partners] == [2, 1]
    assert all(p["discount_percent"] == 0 for p in partners)


def test_empty_database(connection):
    connection.execute("DELETE FROM partners")
    assert get_partners_with_discounts(connection) == []


def test_unknown_partner(connection):
    assert get_partner_with_discount(connection, 999) is None


@pytest.mark.parametrize("partner_id", [0, -1, True, "1 OR 1=1", 1.5])
def test_reject_invalid_id(partner_id):
    with pytest.raises(ValueError):
        get_partner_with_discount(None, partner_id)
