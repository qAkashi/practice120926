from configparser import ConfigParser
from getpass import getpass
import os
from pathlib import Path

import psycopg


def connect_database():
    config = ConfigParser(interpolation=None)
    config.read(Path(__file__).with_name("database.ini"), encoding="utf-8")
    settings = config["postgresql"]
    password = os.environ.get("PGPASSWORD")
    if password is None:
        password = getpass("Пароль PostgreSQL (как в pgAdmin): ")
    return psycopg.connect(
        host=os.environ.get("PGHOST", settings["host"]),
        port=os.environ.get("PGPORT", settings["port"]),
        dbname=os.environ.get("PGDATABASE", settings["dbname"]),
        user=os.environ.get("PGUSER", settings["user"]),
        password=password,
        autocommit=True,
        connect_timeout=5,
        options="-c search_path=public",
    )

