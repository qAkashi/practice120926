from pathlib import Path

from runtime import use_project_python


def main():
    use_project_python(__file__)

    import pytest

    directory = Path(__file__).resolve().parent
    return pytest.main(["-c", str(directory / "pytest.ini"), str(directory / "tests"), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())

