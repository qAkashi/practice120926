import os
import sys
from getpass import getpass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from project_paths import calculator_ui_directory, configure_imports, materials_directory

configure_imports()

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
        source=["partner_discount", "partner_service", "partner_history_service",
                "material_calculator", "material_reference_data"],
        branch=True,
        data_file=None,
    )
    measured.start()
    try:
        result = int(pytest.main([
            str(directory / "tests"), str(materials_directory / "tests"),
            str(calculator_ui_directory / "tests"), "--rootdir", str(directory.parent),
            "-c", str(directory / "pytest.ini"), "-v", "-p", "no:cacheprovider",
        ]))
    finally:
        measured.stop()
        if previous_dsn is None:
            os.environ.pop("TEST_DATABASE_DSN", None)
    measured.report(show_missing=True)
    return result


if __name__ == "__main__":
    raise SystemExit(run_final_tests())
