from pathlib import Path

from runtime import use_project_python


def main():
    use_project_python(__file__)

    import psycopg

    from database import connect_database
    from material_calculator import MaterialCalculator
    from partner_service import get_partner_with_discount

    directory = Path(__file__).resolve().parent
    try:
        with connect_database() as connection:
            with connection.transaction():
                connection.execute((directory / "reference_schema.sql").read_text(encoding="utf-8"))
                connection.execute((directory / "reference_data.sql").read_text(encoding="utf-8"))
            partner_rows = connection.execute("SELECT partner_id FROM partners ORDER BY partner_id").fetchall()
            print("Партнёры: объём продаж за весь период и текущая скидка")
            for row in partner_rows:
                partner = get_partner_with_discount(connection, row[0])
                if partner is not None:
                    print(f"{partner['partner_name']}: {partner['total_quantity']} шт., скидка {partner['discount_percent']}%")
            calculator = MaterialCalculator(connection)
            result = calculator.calculate_materials(1, 1, 10, 2.0, 3.0)
            print(f"Расход сырья (тип 1, материал 1, 10 шт., размеры 2 × 3): {result}")
            print(f"Несуществующий тип: {calculator.calculate_materials(2147483647, 1, 10, 2.0, 3.0)}")
            print(f"Отрицательный размер: {calculator.calculate_materials(1, 1, 10, -2.0, 3.0)}")
            print(f"Нулевое количество: {calculator.calculate_materials(1, 1, 0, 2.0, 3.0)}")
            if result == -1:
                print("Проверьте справочники: коэффициент должен быть положительным, брак — от 0 до 100%.")
                return 1
    except psycopg.Error as error:
        print(f"Демонстрация не выполнена ({type(error).__name__}).")
        print("Проверьте службу PostgreSQL, пароль и database.ini. Сначала выполните импорт из первого задания.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

