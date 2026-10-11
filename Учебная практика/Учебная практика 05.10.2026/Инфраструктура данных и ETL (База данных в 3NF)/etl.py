import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys


columns = {
    "partners": ("partner_id", "partner_name", "inn", "email"),
    "products": ("product_id", "product_name", "price"),
    "sales_history": ("sale_id", "partner_id", "product_id", "sale_date", "quantity", "unit_price"),
}
source_columns = columns | {"sales_history": ("sale_id", "partner_id", "product_id", "sale_date", "quantity", "amount")}
date_formats = ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y.%m.%d")


def read_source(path):
    data = path.read_bytes()
    try:
        text = data.decode("utf-8-sig")
        encoding = "UTF-8"
    except UnicodeDecodeError:
        text = data.decode("cp1251")
        encoding = "Windows-1251"
    reader = csv.DictReader(io.StringIO(text, newline=""))
    rows = []
    for row in reader:
        rows.append((reader.line_num, row))
    return reader.fieldnames, rows, encoding, hashlib.sha256(data).hexdigest()


def positive_integer(value):
    text = value.strip()
    if not re.fullmatch(r"[0-9]{1,10}", text) or not 0 < int(text) <= 2147483647:
        raise ValueError("Ожидалось положительное целое число в диапазоне INT")
    return int(text)


def clean_name(value):
    result = " ".join(value.split())
    if not result or len(result) > 200 or "\x00" in result:
        raise ValueError("Название должно содержать от 1 до 200 символов без нулевого символа")
    return result


def money(value):
    try:
        result = Decimal(value.strip().replace(",", "."))
        if not result.is_finite() or not 0 <= result < Decimal("1000000000000"):
            raise ValueError("Сумма или цена вне диапазона DECIMAL(14,2)")
        rounded = result.quantize(Decimal("0.01"))
        if rounded != result:
            raise ValueError("В исходной сумме или цене больше двух десятичных знаков")
        return rounded
    except InvalidOperation as error:
        raise ValueError("Некорректная сумма или цена") from error


def clean_date(value):
    for pattern in date_formats:
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            continue
    raise ValueError("Некорректная дата: ожидается один из пяти форматов исходных файлов")


def normalize_row(table, row, accepted):
    if table == "partners":
        inn = row["inn"].strip()
        email = row["email"].strip().lower()
        if not re.fullmatch(r"[0-9]{10}|[0-9]{12}", inn):
            raise ValueError("ИНН должен содержать 10 или 12 цифр")
        if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email) or "\x00" in email:
            raise ValueError("Некорректный email")
        return dict(zip(columns[table], (
            positive_integer(row["partner_id"]), clean_name(row["partner_name"]), inn, email,
        )))
    if table == "products":
        return dict(zip(columns[table], (
            positive_integer(row["product_id"]), clean_name(row["product_name"]), money(row["price"]),
        )))
    partner_id = positive_integer(row["partner_id"])
    product_id = positive_integer(row["product_id"])
    if partner_id not in {partner["partner_id"] for partner in accepted["partners"]}:
        raise ValueError(f"Несуществующий partner_id={partner_id}")
    if product_id not in {product["product_id"] for product in accepted["products"]}:
        raise ValueError(f"Несуществующий product_id={product_id}")
    quantity = positive_integer(row["quantity"])
    amount = money(row["amount"])
    unit_price = (amount / quantity).quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    # Историческая цена сохраняет сумму продажи независимо от текущей цены в products.
    if (unit_price * quantity).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) != amount:
        raise ValueError("Сумму нельзя сохранить с точностью unit_price DECIMAL(18,4)")
    return dict(zip(columns[table], (
        positive_integer(row["sale_id"]), partner_id, product_id,
        clean_date(row["sale_date"]), quantity, unit_price,
    )))


def prepare_data(raw_directory):
    accepted = {table: [] for table in columns}
    report = {"sources": {}, "changes": [], "rejected": [], "duplicates": [], "review": []}
    amounts = {}
    for table in columns:
        filename = f"{table}_raw.csv"
        headers, rows, encoding, checksum = read_source(raw_directory / filename)
        if tuple(headers or []) != source_columns[table]:
            raise ValueError(f"{filename}: неверный набор столбцов")
        report["sources"][table] = {"file": filename, "encoding": encoding, "sha256": checksum, "input_rows": len(rows)}
        seen = {}
        unique_inn = set()
        unique_email = set()
        for line, raw in rows:
            item = {"file": filename, "line": line, "raw": raw}
            try:
                if None in raw or any(value is None for value in raw.values()):
                    raise ValueError("Количество полей строки не соответствует заголовку")
                record = normalize_row(table, raw, accepted)
                identity = record[columns[table][0]]
                if identity in seen:
                    if record == seen[identity]:
                        report["duplicates"].append(item | {"reason": "Повтор идентичной записи с тем же ID"})
                        continue
                    raise ValueError("Один ID относится к разным записям")
                if table == "partners":
                    if record["inn"] in unique_inn or record["email"] in unique_email:
                        raise ValueError("Повтор ИНН или email при другом ID; требуется ручное разрешение")
                    unique_inn.add(record["inn"])
                    unique_email.add(record["email"])
                seen[identity] = record
                accepted[table].append(record)
                if table == "sales_history":
                    amounts[str(identity)] = str(money(raw["amount"]))
                for field, value in record.items():
                    if field in raw and str(value) != raw[field]:
                        report["changes"].append({"file": filename, "line": line, "field": field,
                                                  "before": raw[field], "after": str(value)})
                if table == "partners" and "..." in record["partner_name"]:
                    report["review"].append({"partner_id": identity,
                                             "message": "Многоточие в названии сохранено: без первоисточника исправлять ФИО нельзя"})
            except ValueError as error:
                report["rejected"].append(item | {"reason": str(error)})
        report["sources"][table]["accepted_rows"] = len(accepted[table])
    report["expected_amounts"] = amounts
    report["accepted_quantity"] = sum(row["quantity"] for row in accepted["sales_history"])
    report["accepted_amount"] = str(sum((Decimal(value) for value in amounts.values()), Decimal("0.00")))
    return accepted, report


def write_outputs(directory, tables, report):
    from psycopg import sql

    cleaned = directory / "cleaned"
    cleaned.mkdir(exist_ok=True)
    script = ["BEGIN;", "SET LOCAL standard_conforming_strings = on;"]
    for table, fields in columns.items():
        with (cleaned / f"{table}.csv").open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(tables[table])
        if tables[table]:
            values = [
                sql.SQL("({})").format(sql.SQL(", ").join(sql.Literal(row[field]) for field in fields))
                for row in tables[table]
            ]
            statement = sql.SQL("INSERT INTO {} ({}) VALUES\n{};").format(
                sql.Identifier(table),
                sql.SQL(", ").join(map(sql.Identifier, fields)),
                sql.SQL(",\n").join(values),
            )
            script.append(statement.as_string())
        key = fields[0]
        statement = sql.SQL(
            "SELECT setval(pg_get_serial_sequence({}, {}), "
            "COALESCE((SELECT MAX({}) FROM {}), 1), EXISTS (SELECT 1 FROM {}));"
        ).format(sql.Literal(table), sql.Literal(key), sql.Identifier(key), sql.Identifier(table), sql.Identifier(table))
        script.append(statement.as_string())
    script.append("COMMIT;")
    (directory / "data.sql").write_text("\n\n".join(script) + "\n", encoding="utf-8")
    (directory / "etl_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (directory / "rejected_rows.csv").open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=("file", "line", "reason", "raw"))
        writer.writeheader()
        for row in report["rejected"]:
            writer.writerow(row | {"raw": json.dumps(row["raw"], ensure_ascii=False)})


def main():
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        raise SystemExit(subprocess.call([str(executable), str(script), *sys.argv[1:]]))
    directory = Path(__file__).resolve().parent
    tables, report = prepare_data(directory / "raw")
    write_outputs(directory, tables, report)
    for table, rows in tables.items():
        print(f"{table}: подготовлено {len(rows)} строк")
    print(f"Отклонено: {len(report['rejected'])}; повторов: {len(report['duplicates'])}")


if __name__ == "__main__":
    main()
