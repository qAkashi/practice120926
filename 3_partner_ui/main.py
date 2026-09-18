import tkinter as tk

from app import PartnerApp
from database import connect_database
from partner_service import get_partners_with_discounts


def load_partners(password):
    with connect_database(password) as connection:
        connection.execute("SET statement_timeout = '10s'")
        return get_partners_with_discounts(connection)


def main():
    root = tk.Tk()
    PartnerApp(root, load_partners=load_partners)
    root.mainloop()


if __name__ == "__main__":
    main()
