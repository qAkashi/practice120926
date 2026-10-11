from pathlib import Path
import subprocess
import sys


def main():
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        return subprocess.call([str(executable), str(script), *sys.argv[1:]])

    import pytest

    return pytest.main(["-c", str(script.with_name("pytest.ini")), str(script.with_name("tests")), "-q"])


if __name__ == "__main__":
    raise SystemExit(main())

