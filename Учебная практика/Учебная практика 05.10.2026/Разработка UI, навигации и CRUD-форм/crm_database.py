from configparser import ConfigParser
from pathlib import Path

import psycopg


def read_settings():
    config = ConfigParser(interpolation=None)
    config.read(Path(__file__).with_name("database.ini"), encoding="utf-8")
    return dict(config["postgresql"])


class DatabaseService:
    def __init__(self, password, settings=None):
        self.settings = dict(settings or read_settings())
        self.password = password

    def call(self, operation, *arguments):
        # Каждый фоновый запрос получает своё соединение, без обмена им между потоками.
        with psycopg.connect(
            **self.settings,
            password=self.password,
            autocommit=True,
            connect_timeout=5,
            options="-c search_path=public -c statement_timeout=8000 -c lock_timeout=5000",
        ) as connection:
            return operation(connection, *arguments)

