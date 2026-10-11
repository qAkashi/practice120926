import os
from uuid import uuid4

import psycopg
from psycopg import sql
import pytest

from audit_paths import etl_directory
from etl import prepare_data, write_outputs


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_DSN"), reason="Нет тестовой PostgreSQL")
@pytest.mark.parametrize("payload", [
    "O'Brien'); DROP TABLE partners; --",
    "Name\\'); DELETE FROM sales_history; --",
    'Имя "компании" с кавычками',
])
def test_export_keeps_special_characters_as_data(tmp_path, payload):
    tables, report = prepare_data(etl_directory / "raw")
    tables["partners"][0]["partner_name"] = payload
    write_outputs(tmp_path, tables, report)
    schema = "export_audit_" + uuid4().hex
    with psycopg.connect(os.environ["TEST_DATABASE_DSN"], autocommit=True) as connection:
        connection.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            connection.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            connection.execute((etl_directory / "schema.sql").read_text(encoding="utf-8"))
            connection.execute((tmp_path / "data.sql").read_text(encoding="utf-8"))
            assert connection.execute("SELECT partner_name FROM partners WHERE partner_id = 1").fetchone()[0] == payload
            assert connection.execute("SELECT COUNT(*) FROM partners").fetchone()[0] == 5
            assert connection.execute("SELECT COUNT(*) FROM sales_history").fetchone()[0] == 5
        finally:
            connection.execute("ROLLBACK")
            connection.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))

