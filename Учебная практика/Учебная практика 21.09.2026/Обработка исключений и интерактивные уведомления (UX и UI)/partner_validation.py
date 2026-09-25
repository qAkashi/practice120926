import re


partner_types = ("ЗАО", "ООО", "ИП", "АО", "ПАО", "ОАО", "ТК")


class PartnerValidationError(ValueError):
    pass


class PartnerNotFoundError(LookupError):
    pass


def validate_partner(values):
    limits = {"company_name": 200, "address": 500, "director_name": 200,
              "contact_email": 254, "inn": 12, "partner_type": 10, "phone": 40}
    labels = {"company_name": "Наименование", "address": "Адрес",
              "director_name": "ФИО директора", "contact_email": "Email",
              "inn": "ИНН", "partner_type": "Тип партнёра", "phone": "Телефон"}
    result = {}
    for key, limit in limits.items():
        value = str(values.get(key) or "").strip()
        if "\x00" in value or len(value) > limit:
            raise PartnerValidationError(f"{labels[key]}: допустимо не более {limit} символов без нулевого символа.")
        result[key] = value
    if not result["company_name"]:
        raise PartnerValidationError("Наименование не должно быть пустым. Введите название партнёра и нажмите «Сохранить».")
    if not result["contact_email"]:
        raise PartnerValidationError("Email не должен быть пустым. Введите адрес компании, например partner@example.ru, и нажмите «Сохранить».")
    if result["partner_type"] not in partner_types:
        raise PartnerValidationError("Выберите тип партнёра из списка.")
    if not re.fullmatch(r"[0-9]{10}|[0-9]{12}", result["inn"]):
        raise PartnerValidationError("ИНН должен содержать 10 или 12 цифр.")
    result["contact_email"] = result["contact_email"].lower()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", result["contact_email"]):
        raise PartnerValidationError("Введите email в формате partner@example.ru.")
    phone = result["phone"]
    if phone and not re.fullmatch(r"\+[0-9 ()-]+", phone):
        raise PartnerValidationError("Телефон: начните с + и кода страны, например +7 (999) 123-45-67.")
    phone = re.sub(r"[ ()-]", "", phone)
    if phone and not re.fullmatch(r"\+[1-9][0-9]{7,14}", phone):
        raise PartnerValidationError("Телефон должен содержать от 8 до 15 цифр после +.")
    result["phone"] = phone or None
    rating = str(values.get("rating", "")).strip()
    if not re.fullmatch(r"[0-9]{1,10}", rating) or int(rating) > 2147483647:
        raise PartnerValidationError(
            "Рейтинг должен быть целым числом от 0 до 2147483647. "
            "Удалите минус, буквы и знаки препинания, введите целое неотрицательное "
            "число и повторите сохранение."
        )
    result["rating"] = int(rating)
    return result
