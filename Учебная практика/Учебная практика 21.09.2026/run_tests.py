from project_paths import configure_imports


def run():
    configure_imports()
    from run_final_tests import run_final_tests
    return run_final_tests()


if __name__ == "__main__":
    raise SystemExit(run())
