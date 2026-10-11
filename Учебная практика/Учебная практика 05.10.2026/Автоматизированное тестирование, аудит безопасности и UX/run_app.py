from pathlib import Path
import runpy
import subprocess
import sys


def main():
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        return subprocess.call([str(executable), str(script), *sys.argv[1:]])

    from audit_paths import configure_paths, ui_directory

    configure_paths()
    runpy.run_path(str(ui_directory / "run_app.py"), run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

