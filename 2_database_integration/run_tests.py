import os
from getpass import getpass
from pathlib import Path

import pytest
from psycopg.conninfo import make_conninfo

from database import connect_database


def run_tests() -> int:
    password = getpass("Пароль PostgreSQL для тестов (ввод скрыт): ")
    with connect_database(password) as connection:
        settings = connection.info.get_parameters()
    settings["password"] = password
    previous_dsn = os.environ.get("TEST_DATABASE_DSN")
    os.environ["TEST_DATABASE_DSN"] = make_conninfo(**settings)
    test_file = Path(__file__).resolve().with_name("test_partner_service.py")
    try:
        return int(pytest.main([str(test_file), "-v", "-p", "no:cacheprovider"]))
    finally:
        if previous_dsn is None:
            os.environ.pop("TEST_DATABASE_DSN", None)
        else:
            os.environ["TEST_DATABASE_DSN"] = previous_dsn


if __name__ == "__main__":
    raise SystemExit(run_tests())
