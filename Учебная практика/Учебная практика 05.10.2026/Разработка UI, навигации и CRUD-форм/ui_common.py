from pathlib import Path
from configparser import Error as ConfigError
import tkinter as tk
from tkinter import ttk

import psycopg

from crm_validation import ValidationError
from crm_repository import PartnerNotFoundError


background = "#ffffff"
foreground = "#181818"
muted = "#606060"
body_font = ("Arial", 11)
heading_font = ("Arial", 20)


class PlaceholderEntry(ttk.Entry):
    def __init__(self, parent, variable, placeholder):
        super().__init__(parent, textvariable=variable)
        self.variable = variable
        self.placeholder = tk.Label(self, text=placeholder, bg=background, fg=muted, font=body_font)
        self.placeholder.bind("<Button-1>", self.focus_input)
        self.bind("<FocusIn>", self.update_placeholder)
        self.bind("<FocusOut>", self.update_placeholder)
        self.trace_id = variable.trace_add("write", self.update_placeholder)
        self.update_placeholder()

    def focus_input(self, event=None):
        self.focus_set()
        self.update_placeholder()

    def update_placeholder(self, *arguments):
        # Подсказка — отдельная метка, её текст никогда не попадает в данные формы.
        if not self.variable.get() and self.focus_get() != self:
            self.placeholder.place(x=5, rely=0.5, anchor="w")
        else:
            self.placeholder.place_forget()

    def destroy(self):
        self.variable.trace_remove("write", self.trace_id)
        super().destroy()


def configure_style(root):
    root.configure(bg=background)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", font=body_font)
    style.configure("TFrame", background=background)
    style.configure("TLabel", background=background, foreground=foreground)
    style.configure("Hint.TLabel", foreground=muted, font=("Arial", 9))
    style.configure("Heading.TLabel", font=heading_font)
    style.configure("TButton", padding=(12, 8), background="#f3f3f3", foreground=foreground)
    style.map("TButton", background=[("active", "#e7e7e7")])
    style.configure("Treeview", background=background, fieldbackground=background, rowheight=32)
    style.configure("Treeview.Heading", font=("Arial", 11, "bold"))
    style.map("Treeview", background=[("selected", "#d9e4ee")], foreground=[("selected", foreground)])


def load_resources(root):
    directory = Path(__file__).with_name("resources")
    # Явный PNG из памяти обходит нестабильную загрузку через -file в Tk 9.
    logo = tk.PhotoImage(master=root, data=(directory / "company_logo.png").read_bytes(), format="png")
    icon = tk.PhotoImage(master=root, data=(directory / "app_icon.png").read_bytes(), format="png")
    root.iconphoto(True, icon)
    return logo, icon


def add_header(window, title, subtitle=""):
    frame = ttk.Frame(window, padding=(22, 16))
    frame.pack(fill="x")
    ttk.Label(frame, image=window.logo_image).pack(side="left", padx=(0, 16))
    text = ttk.Frame(frame)
    text.pack(side="left", fill="x", expand=True)
    ttk.Label(text, text=title, style="Heading.TLabel").pack(anchor="w")
    if subtitle:
        label = ttk.Label(text, text=subtitle, wraplength=650)
        label.pack(anchor="w", pady=(6, 0))
        return label
    return None


def make_table(parent, columns):
    container = ttk.Frame(parent)
    container.pack(fill="both", expand=True, padx=22, pady=8)
    container.rowconfigure(0, weight=1)
    container.columnconfigure(0, weight=1)
    tree = ttk.Treeview(container, columns=[item[0] for item in columns], show="headings", selectmode="browse")
    for key, title, width in columns:
        tree.heading(key, text=title)
        tree.column(key, width=width, minwidth=60, anchor="w")
    vertical = ttk.Scrollbar(container, orient="vertical", command=tree.yview)
    horizontal = ttk.Scrollbar(container, orient="horizontal", command=tree.xview)
    tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    tree.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    return tree


def describe_error(error):
    if isinstance(error, ValidationError):
        return str(error) + "\n\n1. Исправьте указанное поле.\n2. Нажмите «Сохранить» ещё раз."
    if isinstance(error, psycopg.errors.UniqueViolation):
        constraint = error.diag.constraint_name or ""
        field = "ИНН" if "inn" in constraint else "Email" if "email" in constraint else "ИНН или Email"
        return f"{field} уже используется.\n\n1. Проверьте ИНН и Email другого партнёра.\n2. Исправьте совпадающее значение.\n3. Нажмите «Сохранить»."
    if isinstance(error, psycopg.errors.InsufficientPrivilege):
        return "Недостаточно прав PostgreSQL.\n\n1. Попросите администратора проверить права на таблицы и миграцию.\n2. Нажмите «Подключиться» повторно."
    if isinstance(error, psycopg.OperationalError):
        return "Нет связи с PostgreSQL.\n\n1. Проверьте, что служба PostgreSQL запущена.\n2. Проверьте адрес, порт и имя базы в database.ini.\n3. Нажмите «Подключиться» и введите пароль заново. Если карточка открыта, сначала повторите «Сохранить» после восстановления связи."
    if isinstance(error, psycopg.errors.UndefinedTable):
        return "Не найдены таблицы.\n\n1. Выполните run_import.py из первого задания для practice_051026.\n2. Проверьте имя базы в database.ini.\n3. Повторите подключение."
    if isinstance(error, psycopg.IntegrityError):
        return "Данные нарушают ограничения БД.\n\n1. Проверьте обязательные поля, ИНН, Email и рейтинг.\n2. Исправьте данные.\n3. Нажмите «Сохранить»."
    if isinstance(error, psycopg.Error):
        return "Запрос к БД не выполнен.\n\n1. Проверьте подключение PostgreSQL.\n2. Обновите список и проверьте результат предыдущей операции.\n3. Повторите действие при необходимости."
    if isinstance(error, PartnerNotFoundError):
        return "Партнёр больше не существует.\n\n1. Вернитесь на главную форму.\n2. Нажмите «Обновить».\n3. Выберите существующую запись."
    if isinstance(error, (ConfigError, KeyError, OSError)):
        return "Не удалось прочитать настройки или ресурсы.\n\n1. Проверьте наличие database.ini и папки resources.\n2. Восстановите файлы из проекта.\n3. Запустите приложение заново."
    return "Непредвиденная ошибка интерфейса.\n\n1. Запомните введённые данные.\n2. Обновите список и проверьте, сохранилась ли запись, прежде чем повторять добавление.\n3. Если ошибка повторяется, перезапустите приложение."
