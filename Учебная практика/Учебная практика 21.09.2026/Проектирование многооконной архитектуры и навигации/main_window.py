import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import ttk

import theme
from dialogs import show_error, show_saved
from errors import get_error_message, get_partner_error_message
from partner_edit_window import PartnerEditWindow
from partner_repository import load_partner, store_partner
from presentation import format_partner_title, format_phone, format_rating


class MainWindow:

    def __init__(self, root, load_partners, initial_password=None, auto_start=True,
                 read_partner=load_partner, write_partner=store_partner):
        self.root = root
        self.load_partners = load_partners
        self.read_partner = read_partner
        self.write_partner = write_partner
        self.password = initial_password
        self.login_dialog = None
        self.edit_window = None
        self.operations = queue.Queue()
        self.saved_notice = ""
        self.startup_id = None
        self.loading = False
        self.closed = False
        self.results = queue.Queue()
        self.cards = []
        self.title_labels = []
        self.root.title("CRM: Реестр партнеров")
        self.root.geometry("900x780")
        self.root.minsize(660, 480)
        self.root.configure(bg=theme.background)
        self.root.option_add("*Font", theme.body_font)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        resources = Path(__file__).resolve().parent / "resources"
        self.logo_image = tk.PhotoImage(master=root, data=(resources / "company_logo.png").read_bytes())
        self.icon_image = tk.PhotoImage(master=root, data=(resources / "app_icon.png").read_bytes())
        self.root.iconphoto(True, self.icon_image)
        if self.root.tk.call("tk", "windowingsystem") == "win32":
            self.root.iconbitmap(str(resources / "app_icon.ico"))
        self.build_layout()
        self.root.bind("<MouseWheel>", self.on_mousewheel)
        self.root.bind("<F5>", lambda event: self.refresh())
        self.root.bind("<Control-f>", lambda event: self.search_entry.focus_set())
        self.poll_id = self.root.after(100, self.poll_results)
        self.partners = []
        self.show_message("Войдите, чтобы увидеть актуальный список партнеров.")
        if auto_start:
            self.startup_id = self.root.after(150, self.start)

    def start(self):
        self.startup_id = None
        self.refresh()

    def make_label(self, parent, text, **kwargs):
        return tk.Label(
            parent, text=text, bg=theme.background, fg=theme.foreground,
            anchor="w", **kwargs,
        )

    def make_button(self, parent, text, command):
        return tk.Button(
            parent, text=text, command=command,
            bg=theme.button_background, fg=theme.foreground,
            activebackground=theme.button_hover,
            activeforeground=theme.foreground,
            relief="solid", bd=1, padx=16, pady=7, cursor="hand2",
        )

    def build_layout(self):
        header = tk.Frame(self.root, bg=theme.background)
        header.pack(fill="x", padx=26, pady=(24, 18))
        self.make_label(header, "", image=self.logo_image).pack(side="left")
        titles = tk.Frame(header, bg=theme.background)
        titles.pack(side="left", padx=16)
        self.make_label(titles, "Партнёры компании", font=theme.heading_font).pack(anchor="w")
        self.make_label(titles, "Список партнеров и индивидуальные скидки").pack(anchor="w", pady=(5, 0))
        tk.Frame(self.root, bg=theme.border, height=1).pack(fill="x", padx=26)

        actions = tk.Frame(self.root, bg=theme.background)
        actions.pack(fill="x", padx=26, pady=(14, 0))
        self.add_partner_button = self.make_button(
            actions, "Добавить партнера", self.open_partner_editor,
        )
        self.add_partner_button.pack(side="right")
        self.make_label(
            actions, "Двойной щелчок по карточке — редактирование",
            wraplength=340, justify="left",
        ).pack(side="left", padx=(0, 10))

        toolbar = tk.Frame(self.root, bg=theme.background)
        toolbar.pack(fill="x", padx=26, pady=18)
        self.connection_button = self.make_button(toolbar, "Подключиться", self.connect)
        self.connection_button.pack(side="right")
        self.refresh_button = self.make_button(toolbar, "Обновить", self.refresh)
        self.refresh_button.pack(side="right", padx=(8, 10))
        self.search_text = tk.StringVar(master=self.root)
        self.make_label(toolbar, "Поиск:").pack(side="left", padx=(0, 8))
        self.search_entry = tk.Entry(
            toolbar, textvariable=self.search_text,
            bg=theme.background, fg=theme.foreground,
            relief="solid", bd=1, width=22,
        )
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=7)
        self.search_text.trace_add("write", lambda *_: self.render_partners())

        container = tk.Frame(
            self.root, bg=theme.background,
            highlightbackground=theme.border, highlightthickness=1,
        )
        container.pack(fill="both", expand=True, padx=26)
        self.canvas = tk.Canvas(container, bg=theme.background, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=self.canvas.yview)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.cards_frame = tk.Frame(self.canvas, bg=theme.background)
        self.canvas_window = self.canvas.create_window((0, 0), window=self.cards_frame, anchor="nw")
        self.cards_frame.bind("<Configure>", self.update_scroll_region)
        self.canvas.bind("<Configure>", self.resize_cards)
        self.status = tk.StringVar(master=self.root, value="Нет подключения")
        self.make_label(self.root, "", textvariable=self.status).pack(fill="x", padx=26, pady=14)

    def update_scroll_region(self, event=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def resize_cards(self, event):
        self.canvas.itemconfigure(self.canvas_window, width=event.width)
        for label in self.title_labels:
            label.configure(wraplength=max(220, event.width - 175))

    def on_mousewheel(self, event):
        if event.widget.winfo_toplevel() != self.root:
            return
        if self.cards_frame.winfo_reqheight() > self.canvas.winfo_height():
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

    def clear_cards(self):
        for widget in self.cards_frame.winfo_children():
            widget.destroy()
        self.cards = []
        self.title_labels = []
        self.canvas.yview_moveto(0)

    def show_message(self, text):
        self.clear_cards()
        self.make_label(self.cards_frame, text, wraplength=500, justify="left").pack(padx=22, pady=30, anchor="w")

    def render_partners(self):
        if self.loading:
            return
        if self.password is None:
            return
        query = self.search_text.get().strip().casefold()
        partners = [p for p in self.partners if query in p["company_name"].casefold()]
        self.clear_cards()
        for partner in partners:
            self.add_card(partner)
        if not partners:
            message = "Партнеры не найдены. Измените поисковый запрос."
            if not query:
                message = "В базе пока нет партнеров."
            self.show_message(message)
        self.status.set(f"Данные из БД  |  Показано: {len(partners)} из {len(self.partners)}")

    def add_card(self, partner):
        card = tk.Frame(
            self.cards_frame, bg=theme.background,
            highlightbackground=theme.border, highlightthickness=1,
        )
        card.pack(fill="x", padx=16, pady=(14, 0))
        card.columnconfigure(0, weight=1)
        width = max(220, self.canvas.winfo_width() - 175)
        title = self.make_label(
            card, (f"{partner['partner_type']} | {partner['company_name']}"
                   if partner.get("partner_type") else format_partner_title(partner["company_name"])),
            font=theme.card_title_font, wraplength=width, justify="left",
        )
        title.grid(row=0, column=0, sticky="w", padx=(22, 10), pady=(14, 3))
        self.title_labels.append(title)
        self.make_label(card, f"{partner['discount_percent']}%", font=theme.discount_font).grid(
            row=0, column=1, sticky="ne", padx=(8, 32), pady=(14, 0),
        )
        director = partner.get("director_name") or "не указан"
        self.make_label(card, f"Директор: {director}", wraplength=width, justify="left").grid(
            row=1, column=0, sticky="w", padx=22,
        )
        self.make_label(card, format_phone(partner.get("phone"))).grid(row=2, column=0, sticky="w", padx=22)
        email = partner.get("contact_email") or "не указан"
        email_label = self.make_label(card, f"Email: {email}", wraplength=width, justify="left")
        email_label.grid(row=3, column=0, sticky="w", padx=22)
        self.title_labels.append(email_label)
        self.make_label(card, format_rating(partner.get("rating"))).grid(row=4, column=0, sticky="w", padx=22)
        quantity = partner["total_quantity"]
        self.make_label(card, f"Куплено за весь период: {quantity} шт.").grid(
            row=5, column=0, sticky="w", padx=22, pady=(2, 14),
        )
        self.cards.append(card)
        for widget in [card, *card.winfo_children()]:
            widget.bind(
                "<Double-Button-1>",
                lambda event, selected=partner: self.open_partner_editor(selected),
            )

    def open_partner_editor(self, partner=None):
        if self.closed or self.loading:
            return
        if self.login_dialog is not None and self.login_dialog.winfo_exists():
            self.login_dialog.lift()
            return
        if self.editor_is_open():
            self.edit_window.focus_form()
            return
        if partner is not None:
            self.loading = True
            self.set_main_busy(True)
            self.status.set("Загрузка актуальной карточки из БД…")
            # Передаём только ID: данные списка могли устареть после его загрузки.
            self.run_operation("read", self.read_partner, self.password, partner["partner_id"])
            return
        self.show_partner_editor()

    def show_partner_editor(self, partner=None):
        def return_to_main(values):
            if self.closed:
                return
            self.edit_window = None
            self.root.lift()
            self.add_partner_button.focus_set()

        self.edit_window = PartnerEditWindow(
            self.root, on_back=return_to_main, partner=partner,
            icon_image=self.icon_image, on_save=self.save_partner,
        )

    def set_main_busy(self, busy):
        for button in (self.add_partner_button, self.refresh_button, self.connection_button):
            button.configure(state="disabled" if busy else "normal")

    def run_operation(self, kind, callback, *arguments):
        def worker():
            try:
                result = callback(*arguments)
            except Exception as error:
                self.operations.put((kind, False, get_partner_error_message(error, saving=kind == "save")))
            else:
                self.operations.put((kind, True, result))

        threading.Thread(target=worker, daemon=True).start()

    def save_partner(self, values, partner_id):
        if not self.editor_is_open() or self.edit_window.busy:
            return
        if self.password is None:
            self.edit_window.show_error(
                "Нет подключения к БД",
                "Нет подключения к PostgreSQL. Скопируйте введённые данные, вернитесь "
                "в список и нажмите «Подключиться». После входа повторите добавление.",
            )
            return
        self.edit_window.set_busy(True)
        self.run_operation("save", self.write_partner, self.password, values, partner_id)

    def poll_operations(self):
        try:
            kind, success, result = self.operations.get_nowait()
        except queue.Empty:
            return
        if kind == "read":
            self.loading = False
            self.set_main_busy(False)
            if success and result is not None:
                self.show_partner_editor(result)
                self.status.set("Карточка загружена из БД.")
            else:
                message = result or "Партнёр не найден. Нажмите «Обновить» и выберите существующего партнёра."
                self.status.set(message)
                show_error(self.root, "Ошибка загрузки карточки", message)
        elif self.editor_is_open():
            self.edit_window.set_busy(False)
            if success:
                is_editing = self.edit_window.is_editing
                # COMMIT уже подтверждён: предупреждать о потере данных не нужно.
                self.edit_window.close(confirm=False)
                self.saved_notice = f"Партнёр № {result} сохранён. "
                self.search_text.set("")
                self.refresh()
                show_saved(self.root, result, is_editing)
            else:
                self.edit_window.show_error("Ошибка сохранения", result)

    def editor_is_open(self):
        return self.edit_window is not None and self.edit_window.winfo_exists()

    def connect(self):
        if self.loading or self.closed:
            return
        if self.editor_is_open():
            self.edit_window.focus_form()
            return
        if self.login_dialog is not None and self.login_dialog.winfo_exists():
            self.login_dialog.lift()
            return
        dialog = tk.Toplevel(self.root)
        self.login_dialog = dialog
        dialog.title("Подключение")
        dialog.configure(bg=theme.background)
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.iconphoto(False, self.icon_image)
        self.make_label(dialog, "Введите пароль PostgreSQL").pack(padx=24, pady=(22, 10))
        entry = tk.Entry(dialog, show="•", width=30, relief="solid", bd=1)
        entry.pack(padx=24, ipady=6)
        buttons = tk.Frame(dialog, bg=theme.background)
        buttons.pack(padx=24, pady=20, fill="x")

        def submit(event=None):
            self.password = entry.get()
            dialog.destroy()
            self.refresh()

        self.make_button(buttons, "Войти", submit).pack(side="right")
        self.make_button(buttons, "Отмена", dialog.destroy).pack(side="left")
        dialog.bind("<Return>", submit)
        dialog.bind("<Escape>", lambda event: dialog.destroy())
        dialog.update_idletasks()
        dialog.geometry(f"+{self.root.winfo_rootx() + 160}+{self.root.winfo_rooty() + 150}")
        dialog.grab_set()
        entry.focus_set()

    def refresh(self):
        if self.loading or self.closed or self.editor_is_open():
            return
        if self.password is None:
            self.connect()
            return
        self.loading = True
        self.status.set("Загрузка партнеров…")
        self.refresh_button.configure(state="disabled")
        self.connection_button.configure(state="disabled")
        self.add_partner_button.configure(state="disabled")
        self.show_message("Загрузка партнеров…")
        threading.Thread(target=self.fetch_partners, args=(self.password,), daemon=True).start()

    def fetch_partners(self, password):
        try:
            partners = self.load_partners(password)
        except Exception as error:
            self.results.put((False, get_error_message(error)))
        else:
            self.results.put((True, partners))

    def poll_results(self):
        if self.closed:
            return
        self.poll_operations()
        try:
            success, partners = self.results.get_nowait()
        except queue.Empty:
            pass
        else:
            self.loading = False
            self.refresh_button.configure(state="normal")
            self.connection_button.configure(state="normal")
            self.add_partner_button.configure(state="normal")
            if success:
                self.partners = partners
                self.connection_button.configure(text="Сменить вход")
                self.render_partners()
                if self.saved_notice:
                    self.status.set(self.saved_notice + self.status.get())
                    self.saved_notice = ""
            else:
                self.partners = []
                self.password = None
                self.show_message(partners)
                self.status.set("Данные не загружены. Можно повторить подключение.")
                if self.saved_notice:
                    self.status.set(self.saved_notice + "Не удалось обновить список. Повторите подключение.")
                    self.saved_notice = ""
                show_error(self.root, "Ошибка загрузки списка", self.status.get() + "\n\n" + partners)
        self.poll_id = self.root.after(100, self.poll_results)

    def close(self):
        if self.closed:
            return
        if self.editor_is_open() and self.edit_window.busy:
            self.edit_window.message.set("Дождитесь завершения сохранения перед закрытием приложения.")
            return
        if self.editor_is_open():
            if not self.edit_window.close(notify=False):
                return
            self.edit_window = None
        self.closed = True
        self.password = None
        if self.startup_id is not None:
            self.root.after_cancel(self.startup_id)
        self.root.after_cancel(self.poll_id)
        self.root.destroy()
