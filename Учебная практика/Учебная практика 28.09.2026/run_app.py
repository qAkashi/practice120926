import os
import tkinter as tk

from project_paths import configure_imports


def run():
    configure_imports()
    from material_main_window import MainWindow
    from partner_repository import load_partners

    root = tk.Tk()
    MainWindow(root, load_partners, initial_password=os.environ.get("PGPASSWORD"))
    root.mainloop()


if __name__ == "__main__":
    run()
