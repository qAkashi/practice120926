from pathlib import Path
import sys


directory = Path(__file__).resolve().parent
business_directory = directory.parent / "Реализация ядра бизнес-логики (Расчеты и алгоритмы)"


def configure_paths():
    if not business_directory.is_dir():
        raise RuntimeError(f"Не найдена папка бизнес-логики: {business_directory}")
    if str(business_directory) not in sys.path:
        sys.path.append(str(business_directory))

