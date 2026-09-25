
SELECT 'partners' AS table_name, COUNT(*) AS actual_count, 3 AS expected_count FROM partners
UNION ALL
SELECT 'products', COUNT(*), 3 FROM products
UNION ALL
SELECT 'deliveries', COUNT(*), 4 FROM deliveries
UNION ALL
SELECT 'delivery_items', COUNT(*), 4 FROM delivery_items;


SELECT SUM(quantity) AS total_quantity,
       SUM(ROUND(quantity * unit_price, 2))::DECIMAL(24,2) AS total_amount
FROM delivery_items;


SELECT
    (SELECT COUNT(*) FROM deliveries d
     LEFT JOIN partners p ON p.partner_id = d.partner_id
     WHERE p.partner_id IS NULL) AS deliveries_without_partner,
    (SELECT COUNT(*) FROM delivery_items di
     LEFT JOIN deliveries d ON d.delivery_id = di.delivery_id
     WHERE d.delivery_id IS NULL) AS items_without_delivery,
    (SELECT COUNT(*) FROM delivery_items di
     LEFT JOIN products p ON p.product_id = di.product_id
     WHERE p.product_id IS NULL) AS items_without_product;


SELECT COUNT(*) AS deliveries_without_items
FROM deliveries d
WHERE NOT EXISTS (SELECT 1 FROM delivery_items di WHERE di.delivery_id = d.delivery_id);


WITH expected(delivery_id, expected_amount) AS (
    VALUES (101, 25000.00::DECIMAL(24,2)), (102, 18000.50),
           (103, 10500.00), (105, 13500.00)
)
SELECT e.delivery_id, e.expected_amount,
       SUM(ROUND(di.quantity * di.unit_price, 2))::DECIMAL(24,2) AS actual_amount,
       SUM(ROUND(di.quantity * di.unit_price, 2)) = e.expected_amount AS amount_matches
FROM expected e
LEFT JOIN delivery_items di ON di.delivery_id = e.delivery_id
GROUP BY e.delivery_id, e.expected_amount
ORDER BY e.delivery_id;
