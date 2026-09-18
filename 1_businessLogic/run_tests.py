from pathlib import Path

import coverage
import pytest


def run_tests() -> int:
    project_directory = Path(__file__).resolve().parent
    source_file = project_directory / "partner_discount.py"
    test_file = project_directory / "test_partner_discount.py"
    coverage_result = coverage.Coverage(
        branch=True,
        data_file=None,
        include=[str(source_file)],
    )
    coverage_result.start()
    exit_code = pytest.main([str(test_file), "-v", "-p", "no:cacheprovider"])
    coverage_result.stop()
    if exit_code != 0:
        return int(exit_code)
    total_coverage = coverage_result.report(show_missing=True)
    if total_coverage < 100:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run_tests())
