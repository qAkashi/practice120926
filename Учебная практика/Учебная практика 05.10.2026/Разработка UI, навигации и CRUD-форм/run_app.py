from pathlib import Path
import subprocess
import sys


def main():
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        return subprocess.call([str(executable), str(script), *sys.argv[1:]])

    from project_paths import configure_paths

    configure_paths()

    from main_window import MainWindow

    application = MainWindow()
    application.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

