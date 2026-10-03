import os
import threading
from project_paths import crud_directory
from uuid import uuid4

import psycopg
import pytest
from psycopg import sql

import partner_repository
from conftest import wait_until, widget_texts
from partner_service import get_partner_with_discount, save_partner
from partner_validation import PartnerNotFoundError, PartnerValidationError, validate_partner


@pytest.fixture
def partner_values():
    return {
        "company_name": "Тестовый партнёр", "partner_type": "ООО", "rating": "10",
        "address": "Москва, ул. Примерная, д. 1", "director_name": "Иванов Иван Иванович",
        "phone": "+7 (999) 123-45-67", "contact_email": "Test@Example.ru", "inn": "1234567890",
    }


@pytest.fixture
def crud_database(monkeypatch):
    dsn = os.environ["TEST_DATABASE_DSN"]
    schema_name = "test_partner_" + uuid4().hex
    connection = psycopg.connect(dsn, autocommit=True)
    connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema_name)))
    try:
        connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema_name)))
        connection.execute((crud_directory / "schema.sql").read_text(encoding="utf-8-sig"))

        def connect():
            return psycopg.connect(dsn, options=f"-c search_path={schema_name}")

        monkeypatch.setattr(partner_repository, "connect_database", lambda password: connect())
        yield connection, connect, schema_name
    finally:
        connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema_name)))
        connection.close()


def repository_callbacks():
    return partner_repository.load_partners, partner_repository.load_partner, partner_repository.store_partner


def fill_form(editor, values):
    for key, value in values.items():
        editor.values[key].set(value)


def test_create_persists_all_fields_and_zero_discount(crud_database, partner_values):
    connection, connect, _ = crud_database
    _, _, store = repository_callbacks()
    partner_id = store("", partner_values, None)
    partner = get_partner_with_discount(connection, partner_id)
    assert partner["partner_type"] == "ООО"
    assert partner["company_name"] == partner_values["company_name"]
    assert partner["address"] == partner_values["address"]
    assert partner["director_name"] == partner_values["director_name"]
    assert partner["rating"] == 10
    assert partner["phone"] == "+79991234567"
    assert partner["contact_email"] == "test@example.ru"
    assert partner["total_quantity"] == partner["discount_percent"] == 0


def test_update_preserves_primary_key_and_shipment_history(crud_database, partner_values):
    connection, _, _ = crud_database
    partner_id = save_partner(connection, partner_values)
    product_id = connection.execute("INSERT INTO products (product_name) VALUES ('Товар') RETURNING product_id").fetchone()[0]
    delivery_id = connection.execute("""
        INSERT INTO deliveries (partner_id, delivery_date) VALUES (%s, '2026-09-01') RETURNING delivery_id
    """, (partner_id,)).fetchone()[0]
    connection.execute("INSERT INTO delivery_items VALUES (%s, 1, %s, 10000, 20)", (delivery_id, product_id))
    before = connection.execute("SELECT * FROM deliveries JOIN delivery_items USING (delivery_id)").fetchall()
    changed = partner_values | {"company_name": "Новое имя", "partner_id": 999, "rating": "0"}
    assert save_partner(connection, changed, partner_id) == partner_id
    assert connection.execute("SELECT * FROM deliveries JOIN delivery_items USING (delivery_id)").fetchall() == before
    assert connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 1
    assert get_partner_with_discount(connection, partner_id)["discount_percent"] == 5
    with pytest.raises((psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)):
        connection.execute("DELETE FROM partners WHERE partner_id = %s", (partner_id,))


@pytest.mark.parametrize("field", ["inn", "contact_email"])
def test_duplicate_rolls_back_entire_update(crud_database, partner_values, field):
    connection, _, _ = crud_database
    first_id = save_partner(connection, partner_values)
    second = partner_values | {"inn": "9876543210", "contact_email": "second@example.ru"}
    second_id = save_partner(connection, second)
    bad = second | {field: partner_values[field], "company_name": "Не должно сохраниться"}
    with pytest.raises(psycopg.errors.UniqueViolation):
        save_partner(connection, bad, second_id)
    assert get_partner_with_discount(connection, second_id)["company_name"] == second["company_name"]
    assert get_partner_with_discount(connection, first_id)["inn"] == partner_values["inn"]
    assert save_partner(connection, second | {"rating": "2"}, second_id) == second_id


def test_deleted_partner_is_not_recreated(crud_database, partner_values):
    connection, _, _ = crud_database
    with pytest.raises(PartnerNotFoundError):
        save_partner(connection, partner_values, 999)
    assert connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 0


@pytest.mark.parametrize("partner_id", [0, -1, True, "1 OR 1=1"])
def test_invalid_identity_cannot_update(partner_values, partner_id):
    with pytest.raises(ValueError):
        save_partner(None, partner_values, partner_id)


def test_sql_looking_name_is_stored_as_text(crud_database, partner_values):
    connection, _, _ = crud_database
    name = "Компания'); DROP TABLE deliveries; --"
    partner_id = save_partner(connection, partner_values | {"company_name": name})
    assert get_partner_with_discount(connection, partner_id)["company_name"] == name
    assert connection.execute("SELECT COUNT(*) FROM deliveries").fetchone()[0] == 0


@pytest.mark.parametrize("field,value", [
    ("company_name", " "), ("company_name", "x" * 201), ("address", "x" * 501),
    ("director_name", "\x00"), ("partner_type", "неизвестный"), ("inn", "123"),
    ("contact_email", "bad@"), ("rating", "-1"), ("rating", "4.8"),
    ("rating", "2147483648"), ("phone", "abc"), ("phone", "+7999"),
])
def test_validation_prevents_invalid_write(partner_values, field, value):
    with pytest.raises(PartnerValidationError):
        save_partner(None, partner_values | {field: value})


def test_optional_contact_details_and_rating_zero(partner_values):
    result = validate_partner(partner_values | {"phone": "", "address": "", "director_name": "", "rating": "0"})
    assert result["phone"] is None
    assert result["rating"] == 0


def test_ui_create_auto_refresh_and_edit_reads_fresh_data(make_app, crud_database, partner_values):
    connection, connect, _ = crud_database
    load_all, load_one, store = repository_callbacks()
    application = make_app(load_all, initial_password="", auto_start=False, read_partner=load_one, write_partner=store)
    application.open_partner_editor()
    assert application.edit_window.values["company_name"].get() == ""
    fill_form(application.edit_window, partner_values)
    application.edit_window.save_button.invoke()
    wait_until(application, lambda: application.edit_window is None and not application.loading)
    assert len(application.partners) == len(application.cards) == 1
    assert "сохранён" in application.status.get()
    partner_id = application.partners[0]["partner_id"]
    connection.execute("UPDATE partners SET address = 'Актуальный адрес' WHERE partner_id = %s", (partner_id,))
    application.open_partner_editor(application.partners[0])
    wait_until(application, lambda: application.edit_window is not None)
    editor = application.edit_window
    assert editor.partner_id == partner_id
    assert editor.values["address"].get() == "Актуальный адрес"
    editor.values["director_name"].set("Петров Пётр Петрович")
    editor.save_button.invoke()
    wait_until(application, lambda: application.edit_window is None and not application.loading)
    assert application.partners[0]["partner_id"] == partner_id
    assert application.partners[0]["director_name"] == "Петров Пётр Петрович"
    assert "Директор: Петров Пётр Петрович" in widget_texts(application.root)
    assert connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 1


def test_ui_duplicate_preserves_input_and_allows_retry(make_app, crud_database, partner_values):
    connection, connect, _ = crud_database
    save_partner(connection, partner_values)
    load_all, load_one, store = repository_callbacks()
    application = make_app(load_all, initial_password="", auto_start=False, read_partner=load_one, write_partner=store)
    application.open_partner_editor()
    editor = application.edit_window
    fill_form(editor, partner_values)
    editor.save_button.invoke()
    wait_until(application, lambda: not editor.busy)
    assert "ИНН" in editor.message.get()
    assert editor.values["address"].get() == partner_values["address"]
    assert str(editor.save_button.cget("state")) == "normal"
    editor.values["inn"].set("9876543210")
    editor.values["contact_email"].set("another@example.ru")
    editor.save_button.invoke()
    wait_until(application, lambda: application.edit_window is None and not application.loading)
    assert len(application.partners) == 2


def test_ui_deleted_partner_on_read_and_save(make_app, crud_database, partner_values):
    connection, connect, _ = crud_database
    partner_id = save_partner(connection, partner_values)
    load_all, load_one, store = repository_callbacks()
    application = make_app(load_all, initial_password="", auto_start=False, read_partner=load_one, write_partner=store)
    application.open_partner_editor({"partner_id": partner_id})
    wait_until(application, lambda: application.edit_window is not None)
    editor = application.edit_window
    connection.execute("DELETE FROM partners WHERE partner_id = %s", (partner_id,))
    editor.save_button.invoke()
    wait_until(application, lambda: not editor.busy)
    assert "удалён" in editor.message.get()
    assert connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 0
    editor.close()
    application.open_partner_editor({"partner_id": partner_id})
    wait_until(application, lambda: not application.loading)
    assert application.edit_window is None
    assert "удалён" in application.status.get()


def test_slow_save_blocks_duplicate_and_premature_close(make_app, partner_values):
    release = threading.Event()
    calls = []

    def store(password, values, partner_id):
        calls.append(values)
        release.wait(5)
        return 1

    application = make_app(lambda password: [], initial_password="", auto_start=False, write_partner=store)
    application.open_partner_editor()
    editor = application.edit_window
    fill_form(editor, partner_values)
    editor.save_button.invoke()
    try:
        editor.save_button.invoke()
        editor.on_escape()
        application.close()
        assert editor.winfo_exists()
        assert not application.closed
        assert str(editor.save_button.cget("state")) == "disabled"
    finally:
        release.set()
    wait_until(application, lambda: application.edit_window is None and not application.loading)
    assert len(calls) == 1


def test_migration_preserves_existing_data_and_can_repeat(crud_database):
    connection, _, schema_name = crud_database
    connection.execute("""
        ALTER TABLE partners DROP COLUMN partner_type, DROP COLUMN address,
            DROP COLUMN director_name, DROP CONSTRAINT ck_partners_rating;
        ALTER TABLE partners ALTER COLUMN rating TYPE DECIMAL(2,1);
        ALTER TABLE partners ADD CONSTRAINT ck_partners_rating CHECK (rating BETWEEN 0 AND 5);
        INSERT INTO partners (partner_id, company_name, inn, contact_email, rating)
        VALUES (100, 'ООО Пример', '1234567890', 'first@example.ru', 4.8);
        INSERT INTO deliveries (partner_id, delivery_date) VALUES (100, '2026-09-01');
    """)
    migration = (crud_directory / "migrate_partner_card.sql").read_text(encoding="utf-8")
    migration = migration.replace("public.partners", f"{schema_name}.partners")
    for _ in range(2):
        connection.execute(migration)
    partner = get_partner_with_discount(connection, 100)
    assert partner["company_name"] == "Пример"
    assert partner["partner_type"] == "ООО"
    assert str(partner["rating"]) == "4.8"
    assert connection.execute("SELECT partner_id FROM deliveries").fetchone()[0] == 100
    next_id = connection.execute("""
        INSERT INTO partners (company_name, inn, contact_email, rating)
        VALUES ('Следующий', '9876543210', 'next@example.ru', 10) RETURNING partner_id
    """).fetchone()[0]
    assert next_id > 100


@pytest.mark.parametrize("error", [psycopg.OperationalError("offline"), psycopg.errors.QueryCanceled("timeout")])
def test_save_failure_keeps_form_and_restores_buttons(make_app, partner_values, error):
    def fail(password, values, partner_id):
        raise error

    application = make_app(lambda password: [], initial_password="", auto_start=False, write_partner=fail)
    application.open_partner_editor()
    editor = application.edit_window
    fill_form(editor, partner_values)
    editor.save_button.invoke()
    wait_until(application, lambda: not editor.busy)
    assert application.edit_window is editor
    assert editor.values["company_name"].get() == partner_values["company_name"]
    assert str(editor.save_button.cget("state")) == "normal"
    assert "Сохранение…" not in editor.message.get()


def test_committed_save_is_not_reported_as_failed_when_refresh_fails(make_app, partner_values):
    def load_failure(password):
        raise psycopg.OperationalError("offline")

    application = make_app(load_failure, initial_password="", auto_start=False,
                           write_partner=lambda password, values, partner_id: 42)
    application.open_partner_editor()
    fill_form(application.edit_window, partner_values)
    application.edit_window.save_button.invoke()
    wait_until(application, lambda: application.edit_window is None and not application.loading)
    assert "№ 42 сохранён" in application.status.get()
    assert "Не удалось обновить список" in application.status.get()


def test_invalid_form_does_not_call_database(make_app, partner_values):
    calls = []
    application = make_app(lambda password: [], initial_password="", auto_start=False,
                           write_partner=lambda *args: calls.append(args))
    application.open_partner_editor()
    editor = application.edit_window
    fill_form(editor, partner_values | {"contact_email": "bad-email"})
    editor.save_button.invoke()
    assert "email" in editor.message.get()
    assert not editor.busy
    assert not calls
