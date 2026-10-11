import argparse
from configparser import ConfigParser
from getpass import getpass
import os
from pathlib import Path
import subprocess
import sys

from etl import columns, prepare_data, write_outputs


def load_database(connection, tables, schema_path):
    from psycopg import sql

    with connection.transaction():
        present = [connection.execute("SELECT to_regclass(%s)", (table,)).fetchone()[0] is not None for table in columns]
        if any(present) and not all(present):
            raise ValueError("В базе создана только часть таблиц. Проверьте схему; существующие таблицы не удалялись.")
        if not any(present):
            connection.execute(schema_path.read_text(encoding="utf-8"))
        current = {}
        for table, fields in columns.items():
            query = sql.SQL("SELECT {} FROM {} ORDER BY {}").format(
                sql.SQL(", ").join(map(sql.Identifier, fields)), sql.Identifier(table), sql.Identifier(fields[0]),
            )
            current[table] = connection.execute(query).fetchall()
        expected = {table: sorted(tuple(row[field] for field in fields) for row in tables[table])
                    for table, fields in columns.items()}
        if any(current.values()):
            if current == expected:
                return "Данные уже импортированы и совпадают с подготовленным набором."
            raise ValueError("База содержит другие данные. Импорт остановлен без удаления или перезаписи записей.")
        for table, fields in columns.items():
            query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
                sql.Identifier(table), sql.SQL(", ").join(map(sql.Identifier, fields)),
                sql.SQL(", ").join(sql.Placeholder() for field in fields),
            )
            with connection.cursor() as cursor:
                cursor.executemany(query, expected[table])
            sequence_name = connection.execute("SELECT pg_get_serial_sequence(%s, %s)", (table, fields[0])).fetchone()[0]
            maximum = max((row[0] for row in expected[table]), default=1)
            connection.execute("SELECT setval(%s::regclass, %s, %s)", (sequence_name, maximum, bool(expected[table])))
    return "Схема создана, подготовленные данные импортированы."


def main():
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        return subprocess.call([str(executable), str(script), *sys.argv[1:]])

    import psycopg
    from psycopg import sql

    config = ConfigParser(interpolation=None)
    config.read(script.with_name("database.ini"), encoding="utf-8")
    settings = config["postgresql"]
    parser = argparse.ArgumentParser(description="Создание отдельной БД и импорт очищенных CSV")
    parser.add_argument("--host", default=settings["host"])
    parser.add_argument("--port", type=int, default=settings.getint("port"))
    parser.add_argument("--dbname", default=settings["dbname"])
    parser.add_argument("--user", default=settings["user"])
    args = parser.parse_args()
    password = os.environ.get("PGPASSWORD")
    if password is None:
        password = getpass("Пароль PostgreSQL (как в pgAdmin): ")
    directory = script.parent
    tables, report = prepare_data(directory / "raw")
    write_outputs(directory, tables, report)
    credentials = {"host": args.host, "port": args.port, "user": args.user,
                   "password": password, "connect_timeout": 5}
    with psycopg.connect(**credentials, dbname="postgres", autocommit=True) as admin:
        exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (args.dbname,)).fetchone()
        if exists is None:
            admin.execute(sql.SQL("CREATE DATABASE {} ENCODING 'UTF8' TEMPLATE template0").format(sql.Identifier(args.dbname)))
    with psycopg.connect(**credentials, dbname=args.dbname, autocommit=True, options="-c search_path=public") as connection:
        print(load_database(connection, tables, directory / "schema.sql"))
        counts = {table: connection.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table))).fetchone()[0]
                  for table in columns}
        totals = connection.execute("SELECT SUM(quantity), SUM(amount) FROM sales_history_details").fetchone()
        print(f"База: {args.dbname}; сервер: {args.host}:{args.port}")
        for table, count in counts.items():
            print(f"{table}: {count}")
        print(f"Количество: {totals[0]}; сумма: {totals[1]}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(f"Импорт не выполнен: {error}")
        raise SystemExit(1)
