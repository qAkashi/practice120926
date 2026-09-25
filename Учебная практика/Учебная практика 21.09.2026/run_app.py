from project_paths import configure_imports


def run():
    configure_imports()
    from main import main
    main()


if __name__ == "__main__":
    run()
