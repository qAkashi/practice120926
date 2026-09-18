
SELECT p.partner_id, p.company_name, p.inn, p.contact_email, p.phone, p.rating,
       COUNT(d.delivery_id) AS delivery_count
FROM partners p
LEFT JOIN deliveries d ON d.partner_id = p.partner_id
GROUP BY p.partner_id, p.company_name, p.inn, p.contact_email, p.phone, p.rating
ORDER BY p.company_name, p.partner_id;


BEGIN;
WITH new_partner AS (
    INSERT INTO partners (company_name, inn, contact_email, phone, rating)
    VALUES ('Учебный партнер (тест)', '990000000001', 'demo@example.invalid', NULL, NULL)
    RETURNING partner_id
), chosen_product AS (
    INSERT INTO products (product_name)
    VALUES ('Тестовый товар (учебный)')
    ON CONFLICT (product_name) DO UPDATE SET product_name = EXCLUDED.product_name
    RETURNING product_id
), first_delivery AS (
    INSERT INTO deliveries (partner_id, delivery_date)
    SELECT partner_id, DATE '2026-04-01' FROM new_partner
    RETURNING delivery_id
)
INSERT INTO delivery_items (delivery_id, line_number, product_id, quantity, unit_price)
SELECT d.delivery_id, 1, p.product_id, 2, 125.5000
FROM first_delivery d CROSS JOIN chosen_product p
RETURNING delivery_id, line_number, product_id, quantity, unit_price,
          ROUND(quantity * unit_price, 2)::DECIMAL(24,2) AS line_amount;
COMMIT;
rollback;

WITH params AS (
    SELECT 1::INT AS partner_id,
           DATE '2026-03-01' AS date_from,
           DATE '2026-03-31' AS date_to
), history AS (
    SELECT d.delivery_id, d.delivery_date, p.partner_id, p.company_name,
           di.line_number, pr.product_name, di.quantity, di.unit_price,
           ROUND(di.quantity * di.unit_price, 2)::DECIMAL(24,2) AS line_amount
    FROM deliveries d
    JOIN partners p ON p.partner_id = d.partner_id
    JOIN delivery_items di ON di.delivery_id = d.delivery_id
    JOIN products pr ON pr.product_id = di.product_id
    CROSS JOIN params x
    WHERE d.partner_id = x.partner_id
      AND d.delivery_date BETWEEN x.date_from AND x.date_to
)
SELECT delivery_id, delivery_date, partner_id, company_name, line_number,
       product_name, quantity, unit_price, line_amount,
       SUM(line_amount) OVER (PARTITION BY delivery_id)::DECIMAL(24,2) AS delivery_total
FROM history
ORDER BY delivery_date, delivery_id, line_number;
SELECT
    p.company_name,
    p.inn,
    d.delivery_id,
    d.delivery_date,
    pr.product_name,
    di.quantity,
    di.unit_price,
    ROUND(di.quantity * di.unit_price, 2) AS line_amount
FROM public.partners p
JOIN public.deliveries d
    ON d.partner_id = p.partner_id
JOIN public.delivery_items di
    ON di.delivery_id = d.delivery_id
JOIN public.products pr
    ON pr.product_id = di.product_id
WHERE p.inn = '990000000001'
ORDER BY d.delivery_id, di.line_number;

