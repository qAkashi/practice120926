import os
from getpass import getpass
from pathlib import Path

import coverage
import pytest
from psycopg.conninfo import make_conninfo

from database import connect_database


def run_final_tests() -> int:
    previous_dsn = os.environ.get("TEST_DATABASE_DSN")
    if previous_dsn is None:
        password = getpass("Пароль PostgreSQL для финальных тестов: ")
        with connect_database(password) as connection:
            settings = connection.info.get_parameters()
        settings["password"] = password
        os.environ["TEST_DATABASE_DSN"] = make_conninfo(**settings)
    directory = Path(__file__).resolve().parent
    measured = coverage.Coverage(
        source=["partner_discount", "partner_service"],
        branch=True,
        data_file=None,
    )
    measured.start()
    try:
        result = int(pytest.main([str(directory / "tests"), "-v", "-p", "no:cacheprovider"]))
    finally:
        measured.stop()
        if previous_dsn is None:
            os.environ.pop("TEST_DATABASE_DSN", None)
    measured.report(show_missing=True)
    return result


if __name__ == "__main__":
    raise SystemExit(run_final_tests())
