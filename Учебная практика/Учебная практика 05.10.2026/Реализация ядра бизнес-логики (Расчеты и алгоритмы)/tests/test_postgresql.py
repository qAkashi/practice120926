import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from material_calculator import MaterialCalculator
from partner_service import get_partner_with_discount


directory = Path(__file__).resolve().parents[1]
etl_directory = directory.parent / "Инфраструктура данных и ETL (База данных в 3NF)"
pytestmark = pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_DSN"),
    reason="Для интеграционных тестов задайте TEST_DATABASE_DSN",
)


@pytest.fixture
def database():
    schema = "business_test_" + uuid4().hex
    with psycopg.connect(os.environ["TEST_DATABASE_DSN"], autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute((etl_directory / "schema.sql").read_text(encoding="utf-8"))
            connection.execute((etl_directory / "data.sql").read_text(encoding="utf-8"))
            connection.execute((directory / "reference_schema.sql").read_text(encoding="utf-8"))
            connection.execute((directory / "reference_data.sql").read_text(encoding="utf-8"))
            yield connection
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_imported_partners_have_correct_totals(database):
    expected = {1: 2, 2: 1, 3: 3, 4: 10, 5: 1}
    for partner_id, quantity in expected.items():
        partner = get_partner_with_discount(database, partner_id)
        assert partner["total_quantity"] == quantity
        assert partner["discount_percent"] == 0
    assert get_partner_with_discount(database, 999) is None


def test_partner_without_sales_and_live_discount_updates(database):
    partner_id = database.execute(
        "INSERT INTO partners (partner_name, inn, email) VALUES (%s, %s, %s) RETURNING partner_id",
        ("Без продаж", "1234567890", "empty@example.ru"),
    ).fetchone()[0]
    assert get_partner_with_discount(database, partner_id)["discount_percent"] == 0
    assert get_partner_with_discount(database, partner_id)["total_quantity"] == 0
    for quantity, expected in [(9999, 0), (10000, 5), (49999, 5), (50000, 10), (299999, 10), (300000, 15)]:
        database.execute(
            """
            INSERT INTO sales_history (sale_id, partner_id, product_id, sale_date, quantity, unit_price)
            VALUES (2000, %s, 101, DATE '2026-10-05', %s, 1)
            ON CONFLICT (sale_id) DO UPDATE SET quantity = EXCLUDED.quantity
            """,
            (partner_id, quantity),
        )
        assert get_partner_with_discount(database, partner_id)["discount_percent"] == expected


def test_materials_read_live_reference_values(database):
    calculator = MaterialCalculator(database)
    assert calculator.calculate_materials(1, 1, 10, 2, 3) == 95
    assert calculator.calculate_materials(999, 1, 10, 2, 3) == -1
    assert calculator.calculate_materials(1, 999, 10, 2, 3) == -1
    database.execute("UPDATE product_types SET coefficient = 2 WHERE product_type_id = 1")
    database.execute("UPDATE material_types SET defect_percent = 10 WHERE material_type_id = 1")
    assert calculator.calculate_materials(1, 1, 10, 2, 3) == 132
    database.execute((directory / "reference_schema.sql").read_text(encoding="utf-8"))
    database.execute((directory / "reference_data.sql").read_text(encoding="utf-8"))
    assert calculator.calculate_materials(1, 1, 10, 2, 3) == 132


def test_discount_sums_multiple_sales_for_all_dates(database):
    database.execute(
        """
        INSERT INTO sales_history (sale_id, partner_id, product_id, sale_date, quantity, unit_price)
        VALUES (2001, 1, 101, DATE '2020-01-01', 4998, 1),
               (2002, 1, 102, DATE '2026-10-05', 5000, 1)
        """
    )
    partner = get_partner_with_discount(database, 1)
    assert partner["total_quantity"] == 10000
    assert partner["discount_percent"] == 5


def test_database_error_does_not_break_caller_transaction(database):
    calculator = MaterialCalculator(database)
    with database.transaction():
        database.execute("ALTER TABLE material_types RENAME TO missing_material_types")
        assert calculator.calculate_materials(1, 1, 10, 2, 3) == -1
        assert database.execute("SELECT 1").fetchone()[0] == 1
        database.execute("ALTER TABLE missing_material_types RENAME TO material_types")
    assert calculator.calculate_materials(1, 1, 10, 2, 3) == 95
