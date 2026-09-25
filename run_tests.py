from pathlib import Path
import runpy
import subprocess
import sys


def main():
    script = Path(__file__).resolve()
    environment = script.parent / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        raise SystemExit(subprocess.call([str(executable), str(script), *sys.argv[1:]]))
    target = script.parent / 'Учебная практика' / 'Учебная практика 21.09.2026' / 'run_tests.py'
    sys.path.insert(0, str(target.parent))
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
