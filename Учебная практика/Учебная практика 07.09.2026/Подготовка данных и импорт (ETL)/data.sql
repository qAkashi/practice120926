
BEGIN;

INSERT INTO partners (partner_id, company_name, inn, contact_email, phone, rating) VALUES
  (1, 'ООО "Логистик-Экспресс"', '7701234567', 'info@logex.ru', '+79991112233', '4.8'),
  (2, 'ИП Петров А.В.', '5001098765', 'petrov_delivery@mail.ru', NULL, '4.2'),
  (3, 'ТК "Быстрый Путь"', '7812345678', 'speedway@yandex.ru', '+78125554433', NULL);

INSERT INTO products (product_id, product_name) VALUES
  (1, 'Кондиционер для белья'),
  (2, 'Мыло жидкое "Стандарт"'),
  (3, 'Стиральный порошок "Альфа"');

INSERT INTO deliveries (delivery_id, partner_id, delivery_date) VALUES
  (101, 1, '2026-03-01'),
  (102, 2, '2026-03-15'),
  (103, 1, '2026-03-20'),
  (105, 3, '2026-03-25');

INSERT INTO delivery_items (delivery_id, line_number, product_id, quantity, unit_price) VALUES
  (101, 1, 3, 50, '500.0000'),
  (102, 1, 2, 200, '90.0025'),
  (103, 1, 1, 30, '350.0000'),
  (105, 1, 2, 150, '90.0000');

-- Вставлены явные ID. Сдвигаем identity-последовательности, чтобы
-- новые записи приложения получили свободные значения 4, 4 и 106.
SELECT setval(pg_get_serial_sequence('partners', 'partner_id'),
              COALESCE((SELECT MAX(partner_id) FROM partners), 1),
              EXISTS (SELECT 1 FROM partners));
SELECT setval(pg_get_serial_sequence('products', 'product_id'),
              COALESCE((SELECT MAX(product_id) FROM products), 1),
              EXISTS (SELECT 1 FROM products));
SELECT setval(pg_get_serial_sequence('deliveries', 'delivery_id'),
              COALESCE((SELECT MAX(delivery_id) FROM deliveries), 1),
              EXISTS (SELECT 1 FROM deliveries));
COMMIT;
