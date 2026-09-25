
\set ON_ERROR_STOP on
\encoding UTF8
BEGIN;

\copy partners (partner_id, company_name, inn, contact_email, phone, rating) FROM 'cleaned/partners.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '')
\copy products (product_id, product_name) FROM 'cleaned/products.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '')
\copy deliveries (delivery_id, partner_id, delivery_date) FROM 'cleaned/deliveries.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '')
\copy delivery_items (delivery_id, line_number, product_id, quantity, unit_price) FROM 'cleaned/delivery_items.csv' WITH (FORMAT csv, HEADER true, ENCODING 'UTF8', NULL '')


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
