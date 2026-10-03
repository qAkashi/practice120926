-- Для проверки в pgAdmin замените 1 на ID нужного партнёра.
WITH params AS (SELECT 1::INT AS partner_id)
SELECT pr.product_name AS "Наименование продукции",
       di.quantity AS "Количество (шт.)",
       to_char(d.delivery_date, 'DD.MM.YYYY') AS "Дата продажи"
FROM deliveries AS d
JOIN delivery_items AS di ON di.delivery_id = d.delivery_id
JOIN products AS pr ON pr.product_id = di.product_id
JOIN params AS p ON p.partner_id = d.partner_id
ORDER BY d.delivery_date DESC, d.delivery_id DESC, di.line_number;
