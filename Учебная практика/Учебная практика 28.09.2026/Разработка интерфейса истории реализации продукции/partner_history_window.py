import queue
import threading
import tkinter as tk
from tkinter import font, ttk

import theme
from dialogs import show_error
from errors import get_partner_error_message


class PartnerHistoryWindow(tk.Toplevel):
    def __init__(self, parent, partner_id, partner_name, load_history, on_back,
                 logo_image, icon_image):
        super().__init__(parent)
        self.withdraw()
        self.partner_id = partner_id
        self.load_history = load_history
        self.on_back = on_back
        self.logo_image = logo_image
        self.icon_image = icon_image
        self.closed = False
        self.loading = False
        self.results = queue.Queue()
        self.title(f"CRM: История реализации продукции — {partner_name}")
        self.configure(bg=theme.background)
        self.geometry("860x560")
        self.minsize(660, 420)
        self.transient(parent)
        self.iconphoto(False, self.icon_image)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", self.on_escape)
        self.build_layout(partner_name)
        self.poll_id = self.after(100, self.poll_results)
        self.geometry(f"+{max(0, parent.winfo_rootx() + 20)}+{max(0, parent.winfo_rooty() + 40)}")
        self.deiconify()
        self.grab_set()
        self.back_button.focus_set()
        self.refresh()

    def build_layout(self, partner_name):
        header = tk.Frame(self, bg=theme.background)
        header.pack(fill="x", padx=26, pady=(24, 18))
        tk.Label(header, image=self.logo_image, bg=theme.background).pack(side="left")
        titles = tk.Frame(header, bg=theme.background)
        titles.pack(side="left", padx=16, fill="x", expand=True)
        heading = tk.Label(titles, text="История реализации продукции", font=theme.heading_font,
                           bg=theme.background, fg=theme.foreground, anchor="w", justify="left")
        heading.pack(fill="x")
        self.partner_label = tk.Label(titles, text=partner_name, font=theme.body_font,
                                     bg=theme.background, fg=theme.foreground,
                                     anchor="w", justify="left", wraplength=590)
        self.partner_label.pack(fill="x", pady=(5, 0))
        titles.bind("<Configure>", lambda event: (
            heading.configure(wraplength=event.width),
            self.partner_label.configure(wraplength=event.width),
        ))
        tk.Frame(self, bg=theme.border, height=1).pack(fill="x", padx=26)
        self.status = tk.StringVar(master=self)
        tk.Label(self, textvariable=self.status, font=theme.body_font, anchor="w",
                 bg=theme.background, fg=theme.muted, wraplength=760, justify="left").pack(
                     fill="x", padx=26, pady=14)

        # Нижняя панель получает место до таблицы, чтобы кнопки не скрывались при уменьшении окна.
        buttons = tk.Frame(self, bg=theme.background)
        buttons.pack(side="bottom", fill="x", padx=26, pady=18)
        self.back_button = self.make_button(buttons, "Назад", self.close)
        self.back_button.pack(side="right")
        self.refresh_button = self.make_button(buttons, "Обновить", self.refresh)
        self.refresh_button.pack(side="right", padx=(0, 12))
        container = tk.Frame(self, bg=theme.background)
        container.pack(fill="both", expand=True, padx=26)
        container.rowconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        style = ttk.Style(self)
        style.configure("History.Treeview", font=theme.body_font, rowheight=32,
                        background=theme.background, fieldbackground=theme.background,
                        foreground=theme.foreground)
        style.configure("History.Treeview.Heading", font=theme.body_font,
                        background=theme.button_background, foreground=theme.foreground)
        style.map("History.Treeview", background=[("selected", theme.button_hover)],
                  foreground=[("selected", theme.foreground)])
        self.table = ttk.Treeview(container, columns=("product", "quantity", "date"),
                                  show="headings", style="History.Treeview", selectmode="browse")
        self.table.heading("product", text="Наименование продукции")
        self.table.heading("quantity", text="Количество (шт.)")
        self.table.heading("date", text="Дата продажи")
        self.table.column("product", width=460, minwidth=280, anchor="w")
        self.table.column("quantity", width=150, minwidth=150, anchor="center", stretch=False)
        self.table.column("date", width=140, minwidth=140, anchor="center", stretch=False)
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(container, orient="vertical", command=self.table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(container, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)

    def make_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, font=theme.body_font,
                         bg=theme.button_background, fg=theme.foreground,
                         activebackground=theme.button_hover, activeforeground=theme.foreground,
                         relief="solid", bd=1, padx=16, pady=7, cursor="hand2")

    def refresh(self):
        if self.closed or self.loading:
            return
        self.loading = True
        self.status.set("Загрузка истории продаж…")
        self.refresh_button.configure(state="disabled")
        self.table.delete(*self.table.get_children())
        threading.Thread(target=self.fetch_history, daemon=True).start()

    def fetch_history(self):
        try:
            history = self.load_history(self.partner_id)
        except Exception as error:
            self.results.put((False, get_partner_error_message(error)))
        else:
            self.results.put((True, history))

    def poll_results(self):
        if self.closed:
            return
        try:
            success, result = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.loading = False
            self.refresh_button.configure(state="normal")
            if success:
                self.display_history(result)
            else:
                self.status.set("История не загружена. Проверьте подключение и нажмите «Обновить».")
                show_error(self, "Ошибка загрузки истории", result)
        self.poll_id = self.after(100, self.poll_results)

    def display_history(self, history):
        name = " ".join(filter(None, (history.get("partner_type"), history["company_name"])))
        self.title(f"CRM: История реализации продукции — {name}")
        self.partner_label.configure(text=name)
        rows = history["rows"]
        text_font = font.Font(self, font=theme.body_font)
        width = max([460, *(text_font.measure(row["product_name"]) + 24 for row in rows)])
        self.table.column("product", width=width)
        for row in rows:
            self.table.insert("", "end", values=(row["product_name"], row["quantity"],
                                                   row["delivery_date"].strftime("%d.%m.%Y")))
        if rows:
            quantity = sum(row["quantity"] for row in rows)
            self.status.set(f"Позиций отгрузок: {len(rows)}  |  Всего продукции: {quantity} шт.  |  За весь период")
        else:
            self.status.set("У этого партнёра пока нет отгрузок.")

    def focus_window(self):
        if not self.closed:
            self.lift()
            self.back_button.focus_set()

    def on_escape(self, event=None):
        self.close()
        return "break"

    def close(self, notify=True):
        if self.closed:
            return
        self.closed = True
        self.after_cancel(self.poll_id)
        if self.grab_current() == self:
            self.grab_release()
        self.destroy()
        if notify:
            self.on_back()
