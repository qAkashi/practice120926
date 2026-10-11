BEGIN;

SET LOCAL standard_conforming_strings = on;

INSERT INTO "partners" ("partner_id", "partner_name", "inn", "email") VALUES
(1, 'ООО "Вектор"', '7701234567', 'vector@mail.ru'),
(2, 'ИП ...Петров A.B.', '7802345678', 'petrov@yandex.ru'),
(3, 'АО "Технолоджис"', '5003456789', 'info@techno.ru'),
(4, 'ООО "Альфа"', '7704567890', 'alpha@gmail.com'),
(5, 'ИП Сидоров И.И.', '7805678901', 'sidorov@llc.ru');

SELECT setval(pg_get_serial_sequence('partners', 'partner_id'), COALESCE((SELECT MAX("partner_id") FROM "partners"), 1), EXISTS (SELECT 1 FROM "partners"));

INSERT INTO "products" ("product_id", "product_name", "price") VALUES
(101, 'Ноутбук Pro', 75000.00),
(102, 'Смартфон X', 45000.50),
(103, 'Монитор 27"', 18200.00);

SELECT setval(pg_get_serial_sequence('products', 'product_id'), COALESCE((SELECT MAX("product_id") FROM "products"), 1), EXISTS (SELECT 1 FROM "products"));

INSERT INTO "sales_history" ("sale_id", "partner_id", "product_id", "sale_date", "quantity", "unit_price") VALUES
(1001, 1, 101, '2023-10-25'::date, 2, 75000.0000),
(1002, 2, 102, '2023-10-26'::date, 1, 45000.5000),
(1004, 4, 103, '2023-10-28'::date, 10, 18200.0000),
(1005, 3, 102, '2023-10-29'::date, 3, 45000.5000),
(1006, 5, 103, '2023-10-30'::date, 1, 18200.0000);

SELECT setval(pg_get_serial_sequence('sales_history', 'sale_id'), COALESCE((SELECT MAX("sale_id") FROM "sales_history"), 1), EXISTS (SELECT 1 FROM "sales_history"));

COMMIT;
