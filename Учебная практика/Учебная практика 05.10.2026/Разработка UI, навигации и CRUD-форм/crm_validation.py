import re


partner_types = ("ЗАО", "ООО", "ИП", "АО", "ПАО", "ОАО")
field_names = ("partner_name", "partner_type", "rating", "address", "director_name", "phone", "email", "inn")


class ValidationError(ValueError):
    def __init__(self, field, message):
        super().__init__(message)
        self.field = field


def validate_partner(values):
    result = {field: str(values.get(field, "")).strip() for field in field_names}
    for field, maximum in (
        ("partner_name", 200), ("address", 500), ("director_name", 200),
        ("phone", 32), ("email", 254), ("inn", 12),
    ):
        if len(result[field]) > maximum or "\x00" in result[field]:
            raise ValidationError(field, f"Уберите недопустимые символы. Допустимо не более {maximum} символов.")
    if not result["partner_name"]:
        raise ValidationError("partner_name", "Введите наименование партнёра.")
    if result["partner_type"] not in partner_types:
        raise ValidationError("partner_type", "Выберите тип партнёра из выпадающего списка.")
    if not re.fullmatch(r"[0-9]{1,10}", result["rating"]) or int(result["rating"]) > 2147483647:
        raise ValidationError("rating", "Рейтинг должен быть целым числом от 0 до 2147483647. Удалите минус, буквы и дробную часть.")
    result["rating"] = int(result["rating"])
    result["email"] = result["email"].lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", result["email"]):
        raise ValidationError("email", "Введите Email в формате partner@example.ru, без пробелов.")
    if not re.fullmatch(r"(?:[0-9]{10}|[0-9]{12})", result["inn"]):
        raise ValidationError("inn", "Введите ИНН: 10 или 12 цифр без пробелов.")
    if result["phone"]:
        digits = re.sub(r"[^0-9]", "", result["phone"])
        if not re.fullmatch(r"\+?[0-9 ()-]+", result["phone"]) or not 10 <= len(digits) <= 15:
            raise ValidationError("phone", "Укажите телефон, например +7 (999) 123-45-67, или оставьте поле пустым.")
    return result

