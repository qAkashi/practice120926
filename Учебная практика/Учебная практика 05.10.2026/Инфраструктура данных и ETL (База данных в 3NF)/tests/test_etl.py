from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from etl import clean_date, money, prepare_data, write_outputs


directory = Path(__file__).resolve().parents[1]


def test_provided_files_are_cleaned_without_losing_amounts():
    tables, report = prepare_data(directory / "raw")
    assert {key: len(rows) for key, rows in tables.items()} == {"partners": 5, "products": 3, "sales_history": 5}
    assert tables["partners"][0]["partner_name"] == 'ООО "Вектор"'
    assert tables["partners"][1]["partner_name"] == 'ИП ...Петров A.B.'
    assert tables["partners"][3]["email"] == "alpha@gmail.com"
    assert tables["products"][0]["product_name"] == "Ноутбук Pro"
    assert report["sources"]["products"]["encoding"] == "Windows-1251"
    assert len(report["rejected"]) == 1
    assert report["rejected"][0]["raw"]["sale_id"] == "1003"
    assert report["accepted_quantity"] == 17
    assert report["accepted_amount"] == "530202.00"
    assert [row["sale_date"] for row in tables["sales_history"]] == [date(2023, 10, day) for day in (25, 26, 28, 29, 30)]


@pytest.mark.parametrize("text", ["25.10.2023", "2023/10/25", "25-10-2023", "2023.10.25", " 2023-10-25 "])
def test_supported_date_formats(text):
    assert clean_date(text) == date(2023, 10, 25)


@pytest.mark.parametrize("text", ["31.02.2023", "", "10/25/2023", "yesterday"])
def test_invalid_dates_are_rejected(text):
    with pytest.raises(ValueError):
        clean_date(text)


@pytest.mark.parametrize("text", ["NaN", "Infinity", "-1", "1.001", "1000000000000"])
def test_invalid_money_is_rejected(text):
    with pytest.raises(ValueError):
        money(text)


def test_duplicates_and_other_broken_keys_are_quarantined(tmp_path):
    for path in (directory / "raw").glob("*.csv"):
        (tmp_path / path.name).write_bytes(path.read_bytes())
    with (tmp_path / "partners_raw.csv").open("a", encoding="utf-8") as output:
        output.write('\n1,"ООО ""Вектор""",7701234567,vector@mail.ru\n')
        output.write('6,Другой,7709999999,VECTOR@MAIL.RU\n')
    with (tmp_path / "sales_history_raw.csv").open("a", encoding="utf-8") as output:
        output.write('\n1007,1,999,2023-10-31,1,20\n1008,1,101,31.02.2023,1,75000\n')
    tables, report = prepare_data(tmp_path)
    assert len(tables["partners"]) == 5
    assert len(tables["sales_history"]) == 5
    assert len(report["duplicates"]) == 1
    assert len(report["rejected"]) == 4


def test_outputs_are_repeatable_and_contain_iso_dates(tmp_path):
    tables, report = prepare_data(directory / "raw")
    write_outputs(tmp_path, tables, report)
    before = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    write_outputs(tmp_path, tables, report)
    after = {str(path.relative_to(tmp_path)): path.read_bytes() for path in tmp_path.rglob("*") if path.is_file()}
    assert before == after
    assert "2023-10-25" in (tmp_path / "cleaned" / "sales_history.csv").read_text(encoding="utf-8")
    for row in tables["sales_history"]:
        assert (row["quantity"] * row["unit_price"]).quantize(Decimal("0.01")) == Decimal(report["expected_amounts"][str(row["sale_id"])])
