CREATE TABLE IF NOT EXISTS product_types (
    product_type_id INT PRIMARY KEY CHECK (product_type_id > 0),
    type_name VARCHAR(100) NOT NULL UNIQUE CHECK (btrim(type_name) <> ''),
    coefficient DECIMAL(12,6) NOT NULL
        CHECK (coefficient > 0 AND coefficient <> 'NaN'::numeric)
);

CREATE TABLE IF NOT EXISTS material_types (
    material_type_id INT PRIMARY KEY CHECK (material_type_id > 0),
    type_name VARCHAR(100) NOT NULL UNIQUE CHECK (btrim(type_name) <> ''),
    defect_percent DECIMAL(7,4) NOT NULL
        CHECK (defect_percent BETWEEN 0 AND 100)
);

