import tkinter as tk

from app import PartnerApp
from partner_discount import calculate_partner_discount


def get_preview_partners():
    partners = [
        {"partner_id": 2, "company_name": "ИП Петров А.В.",
         "phone": None, "rating": "4.2", "total_quantity": 200},
        {"partner_id": 1, "company_name": 'ООО "Логистик-Экспресс"',
         "phone": "+79991112233", "rating": "4.8", "total_quantity": 80},
        {"partner_id": 3, "company_name": 'ТК "Быстрый Путь"',
         "phone": "+78125554433", "rating": None, "total_quantity": 150},
    ]
    for partner in partners:
        partner["discount_percent"] = calculate_partner_discount(partner["total_quantity"])
    return partners


def main():
    root = tk.Tk()
    PartnerApp(root, preview_partners=get_preview_partners())
    root.mainloop()


if __name__ == "__main__":
    main()
