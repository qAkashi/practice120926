from configparser import Error as ConfigError

import psycopg

from partner_validation import PartnerNotFoundError, PartnerValidationError


def get_error_message(error: Exception) -> str:
    if isinstance(error, psycopg.errors.UndefinedColumn):
        return "Обновите структуру БД: выполните migrate_partner_card.sql из папки задания CRUD в pgAdmin."
    if isinstance(error, psycopg.errors.InvalidPassword):
        return "Неверный пароль PostgreSQL. Повторите вход."
    if isinstance(error, psycopg.errors.UndefinedTable):
        return "В выбранной базе нет нужных таблиц. Проверьте имя базы в database.ini."
    if isinstance(error, psycopg.errors.QueryCanceled):
        return "Загрузка заняла слишком много времени. Повторите подключение."
    if isinstance(error, psycopg.OperationalError):
        return ("Не удалось подключиться к PostgreSQL.\n"
                "1. Убедитесь, что служба PostgreSQL запущена.\n"
                "2. Проверьте сервер, порт и базу в database.ini.\n"
                "3. Нажмите «Подключиться», введите пароль и повторите попытку.")
    if isinstance(error, (OSError, ConfigError, KeyError, ValueError)):
        return "Проверьте наличие и содержимое файла database.ini рядом с программой."
    if isinstance(error, psycopg.Error):
        return "Не удалось прочитать партнеров. Проверьте структуру базы и права пользователя."
    return "Не удалось загрузить данные. Повторите подключение."


def get_partner_error_message(error, saving=False):
    if isinstance(error, (PartnerValidationError, PartnerNotFoundError)):
        return str(error)
    if isinstance(error, psycopg.errors.UniqueViolation):
        constraint = error.diag.constraint_name or ""
        if constraint == "uq_partners_inn":
            return "Партнёр с таким ИНН уже существует. Измените ИНН или откройте его карточку."
        if constraint == "uq_partners_contact_email":
            return "Этот email уже используется другим партнёром. Укажите другой адрес или откройте существующую карточку."
        return "Запись с такими уникальными данными уже существует. Проверьте ИНН и email."
    if isinstance(error, (psycopg.errors.ForeignKeyViolation, psycopg.errors.RestrictViolation)):
        return "Операция нарушает связи с другими записями. Изменения отменены. Обновите список."
    if isinstance(error, psycopg.errors.CheckViolation):
        return "Данные не соответствуют ограничениям БД. Проверьте поля и обновление схемы."
    if isinstance(error, psycopg.errors.QueryCanceled):
        return "Операция заняла слишком много времени и отменена. Можно повторить попытку."
    if isinstance(error, psycopg.errors.InvalidPassword):
        return "Неверный пароль PostgreSQL. Скопируйте изменения, вернитесь в список, нажмите «Сменить вход» и введите правильный пароль."
    if saving and isinstance(error, psycopg.OperationalError):
        return ("Связь с БД недоступна или прервана.\n"
                "1. Проверьте службу PostgreSQL и настройки в database.ini.\n"
                "2. Скопируйте введённые данные перед выходом из формы.\n"
                "3. Переподключитесь и проверьте список перед повторным сохранением: "
                "сервер мог успеть записать данные.")
    if isinstance(error, psycopg.errors.UndefinedColumn):
        return get_error_message(error)
    if saving:
        return "Не удалось сохранить карточку. Проверьте подключение, схему БД и права пользователя."
    return get_error_message(error)
