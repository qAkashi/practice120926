from pathlib import Path
import subprocess
import sys


def main():
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        return subprocess.call([str(executable), str(script), *sys.argv[1:]])

    from audit_paths import business_directory, etl_directory, ui_directory

    suites = [etl_directory, business_directory, ui_directory, script.parent]
    failed = False
    for directory in suites:
        print(f"\n{directory.name}", flush=True)
        # Раздельные процессы исключают смешивание одноимённых модулей тестов заданий.
        result = subprocess.run([
            sys.executable, "-m", "pytest", "-c", str(directory / "pytest.ini"),
            str(directory / "tests"), "-q",
        ], cwd=directory, check=False)
        failed = failed or result.returncode != 0
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())

