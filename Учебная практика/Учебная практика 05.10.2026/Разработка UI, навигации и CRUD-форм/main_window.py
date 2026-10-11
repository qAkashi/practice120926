import os
import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

from crm_database import DatabaseService
from crm_repository import get_history, get_partner, list_partners, migrate, save_partner
from partner_edit_window import PartnerEditWindow
from partner_history_window import PartnerHistoryWindow
from ui_common import add_header, configure_style, describe_error, load_resources, make_table


class MainWindow(tk.Tk):
    def __init__(self, service=None, auto_connect=True):
        super().__init__()
        self.title("CRM: Реестр партнёров и скидок")
        self.geometry("1180x690")
        self.minsize(880, 520)
        configure_style(self)
        self.logo_image, self.icon_image = load_resources(self)
        self.service = service
        self.partners = []
        self.child = None
        self.busy = False
        self.closed = False
        self.results = queue.Queue()
        self.protocol("WM_DELETE_WINDOW", self.close)
        add_header(self, "Реестр партнёров", "Контакты, накопительные скидки и история продаж")
        toolbar = ttk.Frame(self, padding=(22, 0))
        toolbar.pack(fill="x")
        self.search = tk.StringVar(self)
        ttk.Label(toolbar, text="Поиск:").pack(side="left", padx=(0, 8))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search, width=30)
        self.search_entry.pack(side="left", fill="x", expand=True, padx=(0, 12))
        self.search.trace_add("write", self.filter_changed)
        self.connect_button = ttk.Button(toolbar, text="Подключиться", command=self.connect)
        self.connect_button.pack(side="right")
        buttons = ttk.Frame(self, padding=(22, 12))
        buttons.pack(side="bottom", fill="x")
        self.add_button = ttk.Button(buttons, text="Добавить партнёра", command=self.add_partner)
        self.add_button.pack(side="left")
        self.edit_button = ttk.Button(buttons, text="Редактировать", command=self.edit_partner)
        self.edit_button.pack(side="left", padx=8)
        self.history_button = ttk.Button(buttons, text="История продаж", command=self.show_history)
        self.history_button.pack(side="left")
        self.refresh_button = ttk.Button(buttons, text="Обновить", command=self.refresh)
        self.refresh_button.pack(side="right")
        self.status = tk.StringVar(self, value="Подключитесь к базе practice_051026.")
        ttk.Label(self, textvariable=self.status).pack(side="bottom", fill="x", padx=22, pady=5)
        self.tree = make_table(self, [
            ("name", "Наименование", 270), ("type", "Тип", 65), ("rating", "Рейтинг", 75),
            ("phone", "Телефон", 160), ("email", "Email", 210),
            ("quantity", "Продано, шт.", 100), ("discount", "Скидка", 75),
        ])
        self.tree.bind("<<TreeviewSelect>>", self.selection_changed)
        self.tree.bind("<Double-1>", self.double_click)
        self.tree.bind("<Return>", self.edit_partner)
        self.poll_id = self.after(50, self.poll_results)
        self.update_controls()
        if auto_connect:
            self.after_idle(self.connect if service is None else self.initialize_database)

    def submit(self, operation, arguments, on_success, on_error=None):
        if self.closed or self.busy:
            return
        self.busy = True
        self.update_controls()
        service = self.service

        def worker():
            try:
                result = service.call(operation, *arguments)
            except Exception as error:
                self.results.put((False, error, on_success, on_error))
            else:
                self.results.put((True, result, on_success, on_error))

        # Рабочий поток не обращается к Tk: результат забирает главный поток.
        try:
            threading.Thread(target=worker, daemon=True).start()
        except RuntimeError as error:
            self.busy = False
            self.report_callback_exception(type(error), error, error.__traceback__)

    def poll_results(self):
        if self.closed:
            return
        try:
            successful, result, on_success, on_error = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.busy = False
            try:
                if successful:
                    on_success(result)
                elif on_error is not None:
                    on_error(result)
                else:
                    self.show_error(result)
            except Exception as error:
                self.report_callback_exception(type(error), error, error.__traceback__)
            finally:
                if not self.closed:
                    self.update_controls()
        if not self.closed:
            self.poll_id = self.after(50, self.poll_results)

    def show_error(self, error):
        self.status.set("Операция не выполнена. Можно повторить попытку.")
        messagebox.showerror("Ошибка работы с данными", describe_error(error), parent=self.child or self)

    def report_callback_exception(self, exception_type, error, traceback):
        # Tk по умолчанию лишь пишет исключение в stderr; сохраняем рабочий UI.
        logging.getLogger(__name__).error("Ошибка обработчика интерфейса: %s", exception_type.__name__)
        if self.closed:
            return
        if self.child is not None and isinstance(self.child, PartnerEditWindow):
            self.child.set_busy(False)
        self.update_controls()
        self.show_error(error)

    def connect(self):
        if self.busy or self.child is not None:
            return
        password = os.environ.get("PGPASSWORD")
        if password is None:
            password = simpledialog.askstring("Подключение к PostgreSQL", "Пароль пользователя postgres:", show="*", parent=self)
        if password is None:
            return
        self.service = DatabaseService(password)
        self.initialize_database()

    def initialize_database(self):
        self.status.set("Подготовка полей карточки партнёра…")
        self.submit(migrate, (), lambda result: self.refresh())

    def selected_id(self):
        selected = self.tree.selection()
        return int(selected[0]) if selected else None

    def update_controls(self):
        enabled = self.service is not None and not self.busy and self.child is None
        self.add_button.configure(state="normal" if enabled else "disabled")
        self.refresh_button.configure(state="normal" if enabled else "disabled")
        selected = enabled and self.selected_id() is not None
        self.edit_button.configure(state="normal" if selected else "disabled")
        self.history_button.configure(state="normal" if selected else "disabled")
        self.connect_button.configure(state="disabled" if self.busy or self.child else "normal")

    def selection_changed(self, event=None):
        self.update_controls()

    def filter_changed(self, *arguments):
        self.render_partners()

    def render_partners(self, selected_id=None, position=None):
        if selected_id is None:
            selected_id = self.selected_id()
        if position is None:
            position = self.tree.yview()[0]
        query = self.search.get().strip().casefold()
        self.tree.delete(*self.tree.get_children())
        for partner in self.partners:
            searchable = " ".join(str(partner.get(key, "")) for key in ("partner_name", "partner_type", "phone", "email", "inn"))
            if query not in searchable.casefold():
                continue
            values = (
                partner["partner_name"], partner["partner_type"], partner["rating"], partner["phone"],
                partner["email"], partner["total_quantity"], f"{partner['discount_percent']}%",
            )
            self.tree.insert("", "end", iid=str(partner["partner_id"]), values=values)
        if selected_id is not None and self.tree.exists(str(selected_id)):
            self.tree.selection_set(str(selected_id))
            self.tree.focus(str(selected_id))
        self.tree.yview_moveto(position)
        self.status.set(f"Показано: {len(self.tree.get_children())} из {len(self.partners)}")
        self.update_controls()

    def refresh(self, select_id=None):
        if self.busy or self.child is not None or self.service is None:
            return
        selection = self.selected_id() if select_id is None else select_id
        position = self.tree.yview()[0]
        self.status.set("Загрузка партнёров…")

        def loaded(partners):
            self.partners = partners
            self.render_partners(selection, position)

        self.submit(list_partners, (), loaded)

    def add_partner(self):
        if self.busy or self.child is not None or self.service is None:
            return
        self.child = PartnerEditWindow(self)
        self.update_controls()

    def double_click(self, event):
        row = self.tree.identify_row(event.y)
        if row:
            self.tree.selection_set(row)
            self.edit_partner()

    def edit_partner(self, event=None):
        partner_id = self.selected_id()
        if self.busy or self.child is not None or partner_id is None:
            return

        def loaded(partner):
            self.child = PartnerEditWindow(self, partner)
            self.update_controls()

        self.submit(get_partner, (partner_id,), loaded)

    def show_history(self):
        partner_id = self.selected_id()
        if self.busy or self.child is not None or partner_id is None:
            return

        def loaded(result):
            partner, rows = result
            self.child = PartnerHistoryWindow(self, partner, rows)
            self.update_controls()

        self.submit(get_history, (partner_id,), loaded)

    def save_card(self, card, values):
        def saved(partner_id):
            card.set_busy(False)
            message = "Партнёр добавлен." if card.partner_id is None else "Изменения сохранены."
            messagebox.showinfo("Успешное сохранение", message, parent=card)
            card.close(saved=True)
            self.refresh(select_id=partner_id)

        def failed(error):
            card.set_busy(False)
            self.show_error(error)

        self.submit(save_partner, (values, card.partner_id), saved, failed)

    def child_closed(self):
        self.child = None
        self.update_controls()
        self.tree.focus_set()

    def close(self):
        if self.child is not None:
            if isinstance(self.child, PartnerEditWindow):
                if not self.child.close():
                    return
            else:
                self.child.close()
        self.closed = True
        self.after_cancel(self.poll_id)
        self.destroy()
