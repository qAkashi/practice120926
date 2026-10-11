import os
from pathlib import Path
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from etl import prepare_data
from run_import import load_database


directory = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_DSN"), reason="Не задано тестовое подключение PostgreSQL")


@pytest.fixture
def database():
    schema = "etl_test_" + uuid4().hex
    with psycopg.connect(os.environ["TEST_DATABASE_DSN"], autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            yield connection
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def test_import_and_repeated_run_preserve_the_same_rows(database):
    tables, _ = prepare_data(directory / "raw")
    load_database(database, tables, directory / "schema.sql")
    assert "уже импортированы" in load_database(database, tables, directory / "schema.sql")
    assert database.execute("SELECT COUNT(*), SUM(quantity), SUM(amount) FROM sales_history_details").fetchone() == (5, 17, 530202)
    assert database.execute("SELECT COUNT(*) FROM sales_history WHERE sale_id = 1003").fetchone()[0] == 0
    next_id = database.execute("INSERT INTO partners(partner_name, inn, email) VALUES ('Новый', '1234567890', 'new@example.ru') RETURNING partner_id").fetchone()[0]
    assert next_id == 6
    with pytest.raises(ValueError, match="другие данные"):
        load_database(database, tables, directory / "schema.sql")
    assert database.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 6


@pytest.mark.parametrize("query", [
    "INSERT INTO partners VALUES (6, 'Другой', '7701234567', 'other@example.ru')",
    "INSERT INTO partners VALUES (6, 'Другой', '1234567890', 'vector@mail.ru')",
    "INSERT INTO partners VALUES (6, NULL, '1234567890', 'other@example.ru')",
    "INSERT INTO partners VALUES (6, 'Другой', '1234567890', 'VECTOR@MAIL.RU')",
    "INSERT INTO sales_history VALUES (2000, 999, 101, '2023-10-31', 1, 75000)",
    "INSERT INTO sales_history VALUES (2000, 1, 999, '2023-10-31', 1, 75000)",
    "INSERT INTO sales_history VALUES (2000, 1, 101, '2023-10-31', 0, 75000)",
    "INSERT INTO sales_history VALUES (2000, 1, 101, '2023-10-31', 1, -1)",
    "DELETE FROM partners WHERE partner_id = 1",
    "DELETE FROM products WHERE product_id = 101",
])
def test_constraints_block_invalid_data(database, query):
    tables, _ = prepare_data(directory / "raw")
    load_database(database, tables, directory / "schema.sql")
    with pytest.raises(psycopg.IntegrityError):
        database.execute(query)


def test_generated_sql_can_be_imported_and_history_price_does_not_change(database):
    database.execute((directory / "schema.sql").read_text(encoding="utf-8"))
    database.execute((directory / "data.sql").read_text(encoding="utf-8"))
    assert database.execute("SELECT amount FROM sales_history_details WHERE sale_id = 1001").fetchone()[0] == 150000
    database.execute("UPDATE products SET price = 1 WHERE product_id = 101")
    assert database.execute("SELECT amount FROM sales_history_details WHERE sale_id = 1001").fetchone()[0] == 150000
