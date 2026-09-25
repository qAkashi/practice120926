import os
import time
import tkinter as tk

import psycopg
import pytest

from app import PartnerApp


@pytest.fixture
def connection():
    database_dsn = os.environ.get("TEST_DATABASE_DSN")
    if not database_dsn:
        pytest.fail("Запустите run_final_tests.py для подключения тестов к PostgreSQL.")
    with psycopg.connect(database_dsn) as test_connection:
        test_connection.execute("SET search_path TO pg_temp")
        test_connection.execute("""
            CREATE TEMP TABLE partners (
                partner_id INT PRIMARY KEY,
                company_name VARCHAR(200),
                inn VARCHAR(12),
                contact_email VARCHAR(254),
                phone VARCHAR(16),
                rating DECIMAL(2,1)
            ) ON COMMIT DROP
        """)
        test_connection.execute("""
            CREATE TEMP TABLE deliveries (
                delivery_id INT PRIMARY KEY,
                partner_id INT REFERENCES partners,
                delivery_date DATE
            ) ON COMMIT DROP
        """)
        test_connection.execute("""
            CREATE TEMP TABLE delivery_items (
                delivery_id INT REFERENCES deliveries,
                line_number INT,
                quantity INT,
                PRIMARY KEY (delivery_id, line_number)
            ) ON COMMIT DROP
        """)
        test_connection.execute("""
            INSERT INTO partners VALUES
                (1, 'Первый партнер', '1111111111', 'first@example.invalid', NULL, NULL),
                (2, 'Второй партнер', '2222222222', 'second@example.invalid', '+79991112233', 4.8)
        """)
        yield test_connection
        test_connection.rollback()


@pytest.fixture(scope="session")
def tk_root():
    root = tk.Tk()
    root.withdraw()
    yield root
    root.destroy()


@pytest.fixture
def make_app(tk_root):
    applications = []
    callback_errors = []

    def create_app(loader, **kwargs):
        root = tk.Toplevel(tk_root)
        root.withdraw()
        tk_root.report_callback_exception = lambda *args: callback_errors.append(args)
        application = PartnerApp(root, loader, **kwargs)
        applications.append(application)
        root.update()
        return application

    yield create_app
    for application in applications:
        if not application.closed:
            application.close()
    assert not callback_errors, callback_errors


def wait_until(application, condition, timeout=5):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        application.root.update()
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError("Интерфейс не завершил операцию за отведенное время.")


def widget_texts(widget):
    result = []
    if "text" in widget.keys():
        result.append(str(widget.cget("text")))
    for child in widget.winfo_children():
        result.extend(widget_texts(child))
    return result
