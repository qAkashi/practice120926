from pathlib import Path
import sys

import pytest


directory = Path(__file__).resolve().parent
sys.path.insert(0, str(directory.parent))
from project_paths import configure_imports

configure_imports()


if __name__ == "__main__":
    raise SystemExit(pytest.main([
        str(directory / "tests"), "-c", str(directory / "pytest.ini"),
        "-v", "-p", "no:cacheprovider",
    ]))
