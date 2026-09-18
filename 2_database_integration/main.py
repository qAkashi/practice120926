from configparser import Error as ConfigError
from getpass import getpass
from pprint import pprint

import psycopg

from database import connect_database
from partner_service import get_partner_with_discount


def main() -> None:
    try:
        partner_id = int(input("Введите ID партнера: "))
        if partner_id <= 0:
            raise ValueError("ID должен быть положительным.")
        password = getpass("Пароль PostgreSQL (ввод скрыт): ")
        with connect_database(password) as connection:
            partner = get_partner_with_discount(connection, partner_id)
    except ValueError:
        print("Введите положительный целочисленный ID партнера.")
        return
    except psycopg.Error:
        print("Не удалось прочитать данные PostgreSQL.")
        print("Проверьте сервер, пароль, database.ini и наличие таблиц в базе.")
        return
    except OSError:
        print("Не удалось прочитать файл database.ini рядом с database.py.")
        return
    except (ConfigError, KeyError):
        print("Проверьте раздел postgresql и поля в database.ini.")
        return

    if partner is None:
        print("Партнер с таким ID не найден.")
        return

    pprint(partner, sort_dicts=False)
    print(f"Общий объем: {partner['total_quantity']} шт.")
    print(f"Текущая скидка: {partner['discount_percent']}%")


if __name__ == "__main__":
    main()
