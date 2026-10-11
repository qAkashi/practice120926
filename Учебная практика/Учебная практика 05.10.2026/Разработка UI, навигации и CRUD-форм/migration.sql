ALTER TABLE partners
    ADD COLUMN IF NOT EXISTS partner_type VARCHAR(10) NOT NULL DEFAULT ''
        CHECK (partner_type IN ('', 'ЗАО', 'ООО', 'ИП', 'АО', 'ПАО', 'ОАО')),
    ADD COLUMN IF NOT EXISTS rating INT NOT NULL DEFAULT 0 CHECK (rating >= 0),
    ADD COLUMN IF NOT EXISTS address VARCHAR(500) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS director_name VARCHAR(200) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS phone VARCHAR(32) NOT NULL DEFAULT '';

-- В исходном CSV организационная форма включена в наименование.
-- Полное исходное наименование сохраняется.
UPDATE partners
SET partner_type = split_part(partner_name, ' ', 1)
WHERE partner_type = ''
  AND split_part(partner_name, ' ', 1) IN ('ЗАО', 'ООО', 'ИП', 'АО', 'ПАО', 'ОАО');

