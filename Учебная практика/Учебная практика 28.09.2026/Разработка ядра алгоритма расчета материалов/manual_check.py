from material_calculator import calculate_material_quantity


def main():
    print("Расчёт сырья по учебным мок-справочникам")
    print("Типы продукции: 1 — коэффициент 1.5; 2 — 2.0; 3 — 1.0")
    print("Типы материалов: 1 — брак 5%; 2 — 10%; 3 — 0%")
    try:
        product_type_id = int(input("ID типа продукции: "))
        material_type_id = int(input("ID типа материала: "))
        quantity = int(input("Количество продукции (целое число больше 0): "))
        param_1 = float(input("Параметр 1 (больше 0): ").replace(",", "."))
        param_2 = float(input("Параметр 2 (больше 0): ").replace(",", "."))
        result = calculate_material_quantity(product_type_id, material_type_id, quantity, param_1, param_2)
    except (ValueError, EOFError):
        result = -1
    if result == -1:
        print("Результат: -1. Проверьте ID и введите положительные числа; количество должно быть целым.")
    else:
        print(f"Необходимое количество сырья: {result}")


if __name__ == "__main__":
    main()
