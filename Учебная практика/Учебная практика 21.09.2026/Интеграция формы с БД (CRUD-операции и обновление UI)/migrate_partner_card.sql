BEGIN;

ALTER TABLE public.partners
    ADD COLUMN IF NOT EXISTS partner_type VARCHAR(10) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS address VARCHAR(500) NOT NULL DEFAULT '',
    ADD COLUMN IF NOT EXISTS director_name VARCHAR(200) NOT NULL DEFAULT '';

-- Сохраняем дробные значения старого импорта без округления.
ALTER TABLE public.partners DROP CONSTRAINT IF EXISTS ck_partners_rating;
ALTER TABLE public.partners ALTER COLUMN rating TYPE DECIMAL(12,1);
ALTER TABLE public.partners ADD CONSTRAINT ck_partners_rating
    CHECK (rating IS NULL OR rating BETWEEN 0 AND 2147483647);

UPDATE public.partners
SET partner_type = split_part(company_name, ' ', 1),
    company_name = btrim(substr(company_name, strpos(company_name, ' ') + 1))
WHERE partner_type = ''
  AND company_name ~ '^(ЗАО|ООО|ИП|АО|ПАО|ОАО|ТК) +[^ ]';

ALTER TABLE public.partners DROP CONSTRAINT IF EXISTS ck_partners_type;
ALTER TABLE public.partners ADD CONSTRAINT ck_partners_type
    CHECK (partner_type IN ('', 'ЗАО', 'ООО', 'ИП', 'АО', 'ПАО', 'ОАО', 'ТК'));

-- Импорт с явными ID мог оставить счётчик позади существующих записей.
DO $$
DECLARE
    sequence_name TEXT;
    next_id BIGINT;
    maximum_id BIGINT;
BEGIN
    LOCK TABLE public.partners IN SHARE ROW EXCLUSIVE MODE;
    sequence_name := pg_get_serial_sequence('public.partners', 'partner_id');
    IF sequence_name IS NOT NULL THEN
        SELECT COALESCE(MAX(partner_id), 0) INTO maximum_id FROM public.partners;
        next_id := nextval(sequence_name::regclass);
        PERFORM setval(sequence_name::regclass, GREATEST(next_id, maximum_id), true);
    END IF;
END $$;

COMMIT;
