import re


def format_partner_title(company_name: str) -> str:
    match = re.match(r"^(ООО|ИП|ПАО|ОАО|ЗАО|АО|ТК)\s+(.+)$", company_name)
    if match is None:
        return company_name
    return f"{match.group(1)} | {match.group(2)}"


def format_phone(phone: str | None) -> str:
    if phone is None or phone == "":
        return "Телефон: не указан"
    if re.fullmatch(r"\+7\d{10}", phone):
        return f"+7 {phone[2:5]} {phone[5:8]} {phone[8:10]} {phone[10:12]}"
    return phone


def format_rating(rating) -> str:
    if rating is None:
        return "Рейтинг: не указан"
    return f"Рейтинг: {rating}"
