-- Учебные значения для демонстрации: заказчик не предоставил справочники.
-- Повторный запуск сохраняет ранее заданные коэффициенты и проценты брака.
INSERT INTO product_types (product_type_id, type_name, coefficient)
VALUES
    (1, 'Учебный тип продукции 1', 1.5),
    (2, 'Учебный тип продукции 2', 2.0),
    (3, 'Учебный тип продукции 3', 1.0)
ON CONFLICT DO NOTHING;

INSERT INTO material_types (material_type_id, type_name, defect_percent)
VALUES
    (1, 'Учебный материал 1', 5.0),
    (2, 'Учебный материал 2', 10.0),
    (3, 'Учебный материал 3', 0.57)
ON CONFLICT DO NOTHING;

