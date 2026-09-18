from partner_discount import calculate_partner_discount


total_quantity = int(input("Введите количество купленной продукции: "))
discount = calculate_partner_discount(total_quantity)

print(f"Объем продукции: {total_quantity} шт.")
print(f"Скидка партнера: {discount}%")