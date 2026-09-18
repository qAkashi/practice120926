import os

import psycopg
import pytest

from partner_service import get_partner_with_discount


@pytest.fixture
def connection():
    database_dsn = os.environ.get("TEST_DATABASE_DSN")
    if not database_dsn:
        pytest.skip("Для интеграционных тестов задайте TEST_DATABASE_DSN.")

    with psycopg.connect(database_dsn) as test_connection:
        with test_connection.cursor() as cursor:
            cursor.execute("SET search_path TO pg_temp")
            cursor.execute("""
                CREATE TEMP TABLE partners (
                    partner_id INT PRIMARY KEY,
                    company_name VARCHAR(200),
                    inn VARCHAR(12),
                    contact_email VARCHAR(254),
                    phone VARCHAR(16),
                    rating DECIMAL(2,1)
                ) ON COMMIT DROP
            """)
            cursor.execute("""
                CREATE TEMP TABLE deliveries (
                    delivery_id INT PRIMARY KEY,
                    partner_id INT REFERENCES partners,
                    delivery_date DATE
                ) ON COMMIT DROP
            """)
            cursor.execute("""
                CREATE TEMP TABLE delivery_items (
                    delivery_id INT REFERENCES deliveries,
                    line_number INT,
                    quantity INT,
                    PRIMARY KEY (delivery_id, line_number)
                ) ON COMMIT DROP
            """)
            cursor.execute("""
                INSERT INTO partners (partner_id, company_name)
                VALUES (1, 'Первый партнер'), (2, 'Второй партнер')
            """)
        yield test_connection
        test_connection.rollback()


def test_partner_without_deliveries(connection):
    partner = get_partner_with_discount(connection, 1)
    assert partner["company_name"] == "Первый партнер"
    assert partner["phone"] is None
    assert partner["total_quantity"] == 0
    assert partner["discount_percent"] == 0


def test_unknown_partner(connection):
    assert get_partner_with_discount(connection, 999) is None


@pytest.mark.parametrize(
    ("quantity", "expected_discount"),
    [(9_999, 0), (10_000, 5), (49_999, 5), (50_000, 10),
     (299_999, 10), (300_000, 15), (300_001, 15)],
)
def test_discount_boundaries_from_database(connection, quantity, expected_discount):
    connection.execute("INSERT INTO deliveries VALUES (101, 1, '2026-03-01')")
    connection.execute(
        "INSERT INTO delivery_items VALUES (101, 1, %s)",
        (quantity,),
    )
    partner = get_partner_with_discount(connection, 1)
    assert partner["total_quantity"] == quantity
    assert partner["discount_percent"] == expected_discount


def test_sum_all_deliveries_and_items_only_for_requested_partner(connection):
    connection.execute("""
        INSERT INTO deliveries VALUES
            (101, 1, '2020-01-01'),
            (102, 1, '2026-09-01'),
            (103, 2, '2026-09-01'),
            (104, 1, '2026-09-02')
    """)
    connection.execute("""
        INSERT INTO delivery_items VALUES
            (101, 1, 4000), (101, 2, 4000),
            (102, 1, 2000), (103, 1, 300000)
    """)
    partner = get_partner_with_discount(connection, 1)
    assert partner["total_quantity"] == 10_000
    assert partner["discount_percent"] == 5


def test_repeated_call_reads_updated_quantity(connection):
    connection.execute("INSERT INTO deliveries VALUES (101, 1, '2026-03-01')")
    connection.execute("INSERT INTO delivery_items VALUES (101, 1, 9999)")
    assert get_partner_with_discount(connection, 1)["discount_percent"] == 0
    connection.execute("UPDATE delivery_items SET quantity = 10000")
    assert get_partner_with_discount(connection, 1)["discount_percent"] == 5


def test_empty_delivery(connection):
    connection.execute("INSERT INTO deliveries VALUES (101, 1, '2026-03-01')")
    assert get_partner_with_discount(connection, 1)["total_quantity"] == 0


@pytest.mark.parametrize("partner_id", [0, -1, True, "1 OR 1=1", 1.5])
def test_invalid_partner_id(partner_id):
    with pytest.raises(ValueError):
        get_partner_with_discount(None, partner_id)
