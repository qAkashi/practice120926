def calculate_partner_discount(total_quantity: int) -> int:
    if type(total_quantity) is not int or total_quantity < 0:
        raise ValueError("Общее количество должно быть целым неотрицательным числом.")
    if total_quantity < 10000:
        return 0
    if total_quantity < 50000:
        return 5
    if total_quantity < 300000:
        return 10
    return 15

