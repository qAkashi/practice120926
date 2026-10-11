import tkinter as tk
from tkinter import ttk

from ui_common import add_header, background, make_table


class PartnerHistoryWindow(tk.Toplevel):
    def __init__(self, parent, partner, rows):
        super().__init__(parent)
        self.parent = parent
        self.partner_id = partner["partner_id"]
        self.logo_image = parent.logo_image
        self.closed = False
        self.iconphoto(False, parent.icon_image)
        self.configure(bg=background)
        self.title(f"CRM: История реализации продукции — {partner['partner_name']}")
        self.geometry("900x560")
        self.minsize(720, 450)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", self.on_escape)
        add_header(self, "История реализации продукции", partner["partner_name"])
        buttons = ttk.Frame(self, padding=(22, 14))
        buttons.pack(side="bottom", fill="x")
        ttk.Button(buttons, text="Назад", command=self.close).pack(side="left")
        self.status = tk.StringVar(self)
        ttk.Label(buttons, textvariable=self.status).pack(side="right")
        self.tree = make_table(self, [
            ("product", "Наименование продукции", 450),
            ("date", "Дата продажи", 160),
            ("quantity", "Количество (шт.)", 180),
        ])
        for index, (name, sale_date, quantity) in enumerate(rows):
            self.tree.insert("", "end", iid=str(index), values=(name, sale_date.strftime("%d.%m.%Y"), quantity))
        self.status.set(f"Записей: {len(rows)}" if rows else "У партнёра пока нет продаж.")
        self.grab_set()

    def on_escape(self, event=None):
        self.close()
        return "break"

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.grab_release()
        self.destroy()
        self.parent.child_closed()

