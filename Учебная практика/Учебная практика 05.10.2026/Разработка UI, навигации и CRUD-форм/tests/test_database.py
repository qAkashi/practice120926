import os
from pathlib import Path
import time
from unittest.mock import Mock
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from crm_repository import PartnerNotFoundError, get_history, get_partner, list_partners, migrate, save_partner


directory = Path(__file__).resolve().parents[1]
etl_directory = directory.parent / "Инфраструктура данных и ETL (База данных в 3NF)"
pytestmark = pytest.mark.skipif(not os.environ.get("TEST_DATABASE_DSN"), reason="Нет TEST_DATABASE_DSN")


@pytest.fixture
def database():
    schema = "ui_test_" + uuid4().hex
    with psycopg.connect(os.environ["TEST_DATABASE_DSN"], autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute((etl_directory / "schema.sql").read_text(encoding="utf-8"))
            connection.execute((etl_directory / "data.sql").read_text(encoding="utf-8"))
            migrate(connection)
            yield connection
        finally:
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


def card():
    return {
        "partner_name": "Новый партнёр", "partner_type": "ООО", "rating": "5",
        "address": "Москва", "director_name": "Иванов Иван Иванович", "phone": "+7 (999) 123-45-67",
        "email": "new@example.ru", "inn": "1234567890",
    }


def test_migration_is_repeatable_and_preserves_history(database):
    before = database.execute("SELECT * FROM sales_history ORDER BY sale_id").fetchall()
    migrate(database)
    assert database.execute("SELECT * FROM sales_history ORDER BY sale_id").fetchall() == before
    assert get_partner(database, 1)["partner_type"] == "ООО"
    assert get_partner(database, 2)["partner_type"] == "ИП"
    assert get_partner(database, 1)["rating"] == 0


def test_create_update_and_discount_for_no_sales(database):
    partner_id = save_partner(database, card())
    assert get_partner(database, partner_id)["rating"] == 5
    partner = next(partner for partner in list_partners(database) if partner["partner_id"] == partner_id)
    assert partner["total_quantity"] == 0
    assert partner["discount_percent"] == 0
    changed = card()
    changed["partner_name"] = "Изменённый партнёр"
    changed["rating"] = "10"
    assert save_partner(database, changed, partner_id) == partner_id
    assert get_partner(database, partner_id)["rating"] == 10
    assert get_history(database, partner_id)[1] == []


def test_edit_preserves_id_and_foreign_keys(database):
    partner, before = get_history(database, 1)
    partner["rating"] = "7"
    save_partner(database, partner, 1)
    assert get_history(database, 1)[1] == before
    assert database.execute("SELECT partner_id FROM sales_history WHERE sale_id = 1001").fetchone()[0] == 1


def test_duplicate_email_rolls_back_without_losing_connection(database):
    values = card()
    values["email"] = "vector@mail.ru"
    with pytest.raises(psycopg.errors.UniqueViolation):
        save_partner(database, values)
    assert len(list_partners(database)) == 5
    assert get_partner(database, 1)["email"] == "vector@mail.ru"


def test_sql_text_is_stored_as_literal(database):
    values = card()
    values["partner_name"] = "Test'); DROP TABLE partners; --"
    partner_id = save_partner(database, values)
    assert get_partner(database, partner_id)["partner_name"] == values["partner_name"]
    assert len(list_partners(database)) == 6


def test_missing_partner_cannot_be_recreated_by_update(database):
    with pytest.raises(PartnerNotFoundError):
        save_partner(database, card(), 999)
    with pytest.raises(PartnerNotFoundError):
        get_history(database, 999)
    assert len(list_partners(database)) == 5


def test_history_joins_correct_product_and_date(database):
    partner, rows = get_history(database, 1)
    assert partner["partner_id"] == 1
    assert len(rows) == 1
    assert rows[0][0] == "Ноутбук Pro"
    assert rows[0][1].strftime("%d.%m.%Y") == "25.10.2023"
    assert rows[0][2] == 2


def test_real_database_through_windows(database, monkeypatch):
    from main_window import MainWindow

    schema = database.execute("SELECT current_schema()").fetchone()[0]

    class TestService:
        def call(self, operation, *arguments):
            with psycopg.connect(os.environ["TEST_DATABASE_DSN"], autocommit=True) as connection:
                connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
                return operation(connection, *arguments)

    def wait_for(root, condition):
        deadline = time.monotonic() + 5
        while not condition():
            root.update()
            if time.monotonic() > deadline:
                raise AssertionError("Нет ответа от интерфейса")
            time.sleep(0.01)
        root.update()

    monkeypatch.setattr("tkinter.messagebox.showinfo", Mock())
    root = MainWindow(TestService(), auto_connect=False)
    root.withdraw()
    try:
        root.refresh()
        wait_for(root, lambda: not root.busy)
        assert len(root.tree.get_children()) == 5
        root.add_partner()
        for key, value in card().items():
            root.child.values[key].set(value)
        root.child.save()
        wait_for(root, lambda: root.child is None and not root.busy)
        partner_id = root.selected_id()
        assert len(root.tree.get_children()) == 6
        assert get_partner(database, partner_id)["partner_name"] == "Новый партнёр"
        root.edit_partner()
        wait_for(root, lambda: root.child is not None)
        assert root.child.values["director_name"].get() == "Иванов Иван Иванович"
        root.child.values["partner_name"].set("Новое название")
        root.child.save()
        wait_for(root, lambda: root.child is None and not root.busy)
        assert root.tree.item(str(partner_id), "values")[0] == "Новое название"
        assert get_partner(database, partner_id)["partner_name"] == "Новое название"
        root.show_history()
        wait_for(root, lambda: root.child is not None)
        assert "пока нет продаж" in root.child.status.get()
        root.child.close()
        root.tree.selection_set("1")
        root.show_history()
        wait_for(root, lambda: root.child is not None)
        assert root.child.tree.item("0", "values") == ("Ноутбук Pro", "25.10.2023", "2")
        root.child.close()
        assert root.selected_id() == 1
    finally:
        if root.child is not None:
            root.child.destroy()
            root.child = None
        root.close()
