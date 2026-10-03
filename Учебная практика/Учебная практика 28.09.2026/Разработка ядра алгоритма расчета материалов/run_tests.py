from pathlib import Path

import coverage
import pytest


def run_tests() -> int:
    directory = Path(__file__).resolve().parent
    measured = coverage.Coverage(
        source=["material_calculator", "material_reference_data"],
        branch=True,
        data_file=None,
    )
    measured.start()
    try:
        result = int(pytest.main([
            str(directory / "tests"), "-c", str(directory / "pytest.ini"),
            "-v", "-p", "no:cacheprovider",
        ]))
    finally:
        measured.stop()
    total_coverage = measured.report(show_missing=True)
    if result != 0:
        return result
    return 0 if total_coverage == 100 else 1


if __name__ == "__main__":
    raise SystemExit(run_tests())
