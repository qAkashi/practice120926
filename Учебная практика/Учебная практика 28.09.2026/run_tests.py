from project_paths import configure_imports


if __name__ == "__main__":
    configure_imports()
    from run_final_tests import run_final_tests
    raise SystemExit(run_final_tests())
