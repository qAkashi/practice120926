# Интеграция с БД и агрегация данных (SQL + Backend)

Подключение Psycopg, SUM(quantity), LEFT JOIN и данные партнёра с вычисленной скидкой.

`database.py` читает `database.ini`, `partner_service.py` агрегирует отгрузки
и возвращает партнёра вместе с total_quantity и discount_percent.
История в нашем проекте разделена на deliveries и delivery_items, поэтому
именно они используются вместо условной sales_history из текста задания.
`main.py` демонстрирует получение данных, `run_tests.py` проверяет сервис на временных таблицах.
Пароль PostgreSQL вводится при запуске и не хранится в database.ini.


[К четырём заданиям блока](<../README.md>)
