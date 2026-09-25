def calculate_partner_discount(total_quantity: int) -> int:
    
    if total_quantity < 10_000:
        return 0
    if total_quantity < 50_000:
        return 5
    if total_quantity < 300_000:
        return 10
    return 15
