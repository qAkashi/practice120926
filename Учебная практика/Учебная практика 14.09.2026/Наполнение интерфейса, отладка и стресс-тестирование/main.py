import os
import tkinter as tk

from app import PartnerApp
from database import connect_database
from partner_service import get_partners_with_discounts


def load_partners(password):
    with connect_database(password) as connection:
        return get_partners_with_discounts(connection)


def main():
    root = tk.Tk()
    PartnerApp(
        root,
        load_partners=load_partners,
        initial_password=os.environ.get("PGPASSWORD"),
    )
    root.mainloop()


if __name__ == "__main__":
    main()
