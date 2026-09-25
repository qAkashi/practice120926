from configparser import Error as ConfigError

import psycopg


def get_error_message(error: Exception) -> str:
    if isinstance(error, psycopg.errors.InvalidPassword):
        return "Неверный пароль PostgreSQL. Повторите вход."
    if isinstance(error, psycopg.errors.UndefinedTable):
        return "В выбранной базе нет нужных таблиц. Проверьте имя базы в database.ini."
    if isinstance(error, psycopg.errors.QueryCanceled):
        return "Загрузка заняла слишком много времени. Повторите подключение."
    if isinstance(error, psycopg.OperationalError):
        return "Не удалось подключиться к PostgreSQL. Проверьте сервер, настройки и пароль."
    if isinstance(error, (OSError, ConfigError, KeyError, ValueError)):
        return "Проверьте наличие и содержимое файла database.ini рядом с программой."
    if isinstance(error, psycopg.Error):
        return "Не удалось прочитать партнеров. Проверьте структуру базы и права пользователя."
    return "Не удалось загрузить данные. Повторите подключение."
