SELECT 'partners' AS table_name, COUNT(*) AS actual_count, 5 AS expected_count FROM partners
UNION ALL
SELECT 'products', COUNT(*), 3 FROM products
UNION ALL
SELECT 'sales_history', COUNT(*), 5 FROM sales_history;

-- Должны получиться 17 единиц и 530202.00; исключённая продажа 1003 не учитывается.
SELECT SUM(quantity) AS total_quantity, SUM(amount) AS total_amount FROM sales_history_details;

-- Ожидается 0: битые ссылки не должны попасть в хранилище.
SELECT COUNT(*) AS broken_foreign_keys
FROM sales_history s
LEFT JOIN partners p ON p.partner_id = s.partner_id
LEFT JOIN products pr ON pr.product_id = s.product_id
WHERE p.partner_id IS NULL OR pr.product_id IS NULL;

SELECT COUNT(*) AS excluded_sale_count FROM sales_history WHERE sale_id = 1003;

SELECT sale_id, partner_name, product_name, to_char(sale_date, 'YYYY-MM-DD') AS sale_date,
       quantity, unit_price, amount
FROM sales_history_details ORDER BY sale_id;

-- Проверка каждой сохранённой исходной суммы; во всех строках amount_matches = true.
WITH expected (sale_id, amount) AS (
    VALUES (1001, 150000.00), (1002, 45000.50), (1004, 182000.00),
           (1005, 135001.50), (1006, 18200.00)
)
SELECT e.sale_id, e.amount AS expected_amount, s.amount AS actual_amount,
       COALESCE(e.amount = s.amount, false) AS amount_matches
FROM expected e LEFT JOIN sales_history_details s USING (sale_id) ORDER BY e.sale_id;
