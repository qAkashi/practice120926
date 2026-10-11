from pathlib import Path
import subprocess
import sys


def use_project_python(script_path):
    script = Path(script_path).resolve()
    environment = script.parents[3] / ".venv"
    executable = environment / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if executable.is_file() and Path(sys.prefix).resolve() != environment.resolve():
        raise SystemExit(subprocess.call([str(executable), str(script), *sys.argv[1:]]))

