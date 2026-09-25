from configparser import ConfigParser
from pathlib import Path

import psycopg


def connect_database(password: str) -> psycopg.Connection:
    config_path = Path(__file__).resolve().with_name("database.ini")
    config = ConfigParser(interpolation=None)
    with config_path.open(encoding="utf-8") as config_file:
        config.read_file(config_file)
    settings = config["postgresql"]
    return psycopg.connect(
        host=settings["host"],
        port=settings.getint("port"),
        dbname=settings["dbname"],
        user=settings["user"],
        password=password,
        connect_timeout=5,
        options="-c statement_timeout=10000",
    )
