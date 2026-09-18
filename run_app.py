import runpy
import sys
from pathlib import Path


def main():
    application_directory = Path(__file__).resolve().parent / "4_final_app"
    sys.path.insert(0, str(application_directory))
    runpy.run_path(str(application_directory / "main.py"), run_name="__main__")


if __name__ == "__main__":
    main()
