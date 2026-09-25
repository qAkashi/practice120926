from pathlib import Path
import runpy
import sys


def main():
    target = Path(__file__).resolve().parent / 'Наполнение интерфейса, отладка и стресс-тестирование' / 'run_final_tests.py'
    sys.path.insert(0, str(target.parent))
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
