import os
import tkinter as tk

from main_window import MainWindow
from partner_repository import load_partner, load_partners, store_partner


def main():
    root = tk.Tk()
    MainWindow(
        root,
        load_partners=load_partners,
        initial_password=os.environ.get("PGPASSWORD"),
        read_partner=load_partner,
        write_partner=store_partner,
    )
    root.mainloop()


if __name__ == "__main__":
    main()
