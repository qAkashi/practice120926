from functools import wraps
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


logger = logging.getLogger("partner_crm")
logger.addHandler(logging.NullHandler())
logger.propagate = False


def configure_logging(log_path=None):
    path = Path(log_path) if log_path is not None else Path(__file__).with_name("app.log")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    logger.setLevel(logging.INFO)
    try:
        handler = RotatingFileHandler(path, maxBytes=1_000_000, backupCount=2, encoding="utf-8")
    except OSError:
        handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger.addHandler(handler)
    if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
        logger.warning("Журнал недоступен для записи в файл; ошибки выводятся в консоль.")
    return logger


def log_error(operation, error, message):
    # Сырые исключения драйвера могут содержать пароль или значения полей: записываем безопасное описание.
    description = " ".join(message.split())[:1000]
    logger.error("%s | %s | %s", operation, type(error).__name__, description)


def log_validation(operation, message):
    logger.warning("%s | %s", operation, " ".join(message.split())[:1000])


def logged_operation(operation, callback, describe_error):
    @wraps(callback)
    def wrapped(*args, **kwargs):
        try:
            return callback(*args, **kwargs)
        except Exception as error:
            log_error(operation, error, describe_error(error))
            raise
    return wrapped
