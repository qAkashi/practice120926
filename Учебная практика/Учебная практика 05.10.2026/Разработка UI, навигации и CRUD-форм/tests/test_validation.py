import pytest

from crm_validation import ValidationError, validate_partner


@pytest.fixture
def values():
    return {
        "partner_name": " ООО Пример ", "partner_type": "ООО", "rating": "0",
        "address": "Москва", "director_name": "Иванов Иван Иванович",
        "phone": "+7 (999) 123-45-67", "email": " TEST@example.ru ", "inn": "1234567890",
    }


def test_normalization(values):
    partner = validate_partner(values)
    assert partner["partner_name"] == "ООО Пример"
    assert partner["rating"] == 0
    assert partner["email"] == "test@example.ru"


@pytest.mark.parametrize(("field", "value"), [
    ("partner_name", ""), ("partner_name", " " * 3), ("email", ""),
    ("email", "broken"), ("email", "a @example.ru"), ("partner_type", "Другой"),
    ("rating", "-1"), ("rating", "1.5"), ("rating", "abc"), ("rating", ""),
    ("rating", "2147483648"), ("inn", "12"), ("phone", "abc"),
    ("phone", "+7 123"), ("address", "a" * 501), ("director_name", "\x00"),
])
def test_invalid_fields(values, field, value):
    values[field] = value
    with pytest.raises(ValidationError) as error:
        validate_partner(values)
    assert error.value.field == field


def test_optional_fields_can_be_empty(values):
    for key in ("address", "director_name", "phone"):
        values[key] = ""
    assert validate_partner(values)["phone"] == ""

