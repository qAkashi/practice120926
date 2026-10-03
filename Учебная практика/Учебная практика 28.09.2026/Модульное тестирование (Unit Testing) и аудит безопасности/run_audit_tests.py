from pathlib import Path
import subprocess
import sys


def main() -> int:
    script = Path(__file__).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    # Перезапуск нужен до импорта pytest: VS Code может выбрать Python вне окружения проекта.
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        return subprocess.call([str(executable), str(script), *sys.argv[1:]])

    import pytest

    directory = script.parent
    sys.path.insert(0, str(directory.parent))
    from project_paths import configure_imports, history_directory

    configure_imports()
    sys.path.insert(0, str(history_directory / "tests"))

    return int(pytest.main([
        str(directory / "tests"), "-c", str(directory / "pytest.ini"),
        "-v", "-p", "no:cacheprovider", *sys.argv[1:],
    ]))


if __name__ == "__main__":
    raise SystemExit(main())
