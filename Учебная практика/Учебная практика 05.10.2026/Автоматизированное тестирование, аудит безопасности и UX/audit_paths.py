from pathlib import Path
import sys


directory = Path(__file__).resolve().parent
block_directory = directory.parent
business_directory = block_directory / "Реализация ядра бизнес-логики (Расчеты и алгоритмы)"
ui_directory = block_directory / "Разработка UI, навигации и CRUD-форм"
etl_directory = block_directory / "Инфраструктура данных и ETL (База данных в 3NF)"


def configure_paths():
    for path in (ui_directory, business_directory, etl_directory):
        if str(path) not in sys.path:
            sys.path.append(str(path))

