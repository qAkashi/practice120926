import tkinter as tk
from tkinter import messagebox, ttk

from crm_validation import ValidationError, field_names, partner_types, validate_partner
from ui_common import PlaceholderEntry, add_header, background, describe_error


class PartnerEditWindow(tk.Toplevel):
    def __init__(self, parent, partner=None):
        super().__init__(parent)
        self.parent = parent
        self.partner_id = None if partner is None else partner["partner_id"]
        self.busy = False
        self.closed = False
        self.logo_image = parent.logo_image
        self.iconphoto(False, parent.icon_image)
        self.configure(bg=background)
        mode = "Добавление" if partner is None else "Редактирование"
        self.title(f"CRM: Карточка партнёра [{mode}]")
        self.geometry("800x750")
        self.minsize(760, 700)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", self.on_escape)
        add_header(self, f"{mode} партнёра", "Поля со звёздочкой обязательны.")
        content = ttk.Frame(self, padding=(24, 0))
        content.pack(fill="both", expand=True)
        content.columnconfigure(1, weight=1)
        initial = dict(partner or {})
        initial.setdefault("rating", 0)
        self.values = {}
        self.entries = {}
        labels = {
            "partner_name": "Наименование *", "partner_type": "Тип партнёра *",
            "rating": "Рейтинг *", "address": "Адрес", "director_name": "ФИО директора",
            "phone": "Телефон", "email": "Email компании *", "inn": "ИНН *",
        }
        hints = {
            "partner_name": "Полное наименование, например ООО «Вектор»",
            "partner_type": "Выберите организационно-правовую форму",
            "rating": "Целое число от 0",
            "address": "Город, улица, дом, офис",
            "director_name": "Фамилия Имя Отчество",
            "phone": "Пример: +7 (999) 123-45-67",
            "email": "Пример: partner@example.ru",
            "inn": "10 или 12 цифр",
        }
        for index, key in enumerate(field_names):
            self.values[key] = tk.StringVar(self, value=str(initial.get(key, "")))
            ttk.Label(content, text=labels[key]).grid(row=index, column=0, sticky="nw", padx=(0, 18), pady=(10, 0))
            group = ttk.Frame(content)
            group.grid(row=index, column=1, sticky="ew", pady=(5, 0))
            if key == "partner_type":
                # readonly запрещает ввод произвольной организационной формы.
                entry = ttk.Combobox(group, textvariable=self.values[key], values=partner_types, state="readonly")
            else:
                entry = PlaceholderEntry(group, self.values[key], hints[key])
            if key == "rating":
                entry.configure(validate="key", validatecommand=(self.register(self.rating_allowed), "%P"))
            entry.pack(fill="x", ipady=3)
            ttk.Label(group, text=hints[key], style="Hint.TLabel").pack(anchor="w", pady=(2, 4))
            self.entries[key] = entry
        self.status = tk.StringVar(self, value="Данные сохраняются только по кнопке «Сохранить».")
        ttk.Label(self, textvariable=self.status, wraplength=730).pack(fill="x", padx=24, pady=10)
        buttons = ttk.Frame(self, padding=(24, 10))
        buttons.pack(fill="x", side="bottom")
        self.back_button = ttk.Button(buttons, text="Назад", command=self.close)
        self.back_button.pack(side="left")
        self.save_button = ttk.Button(buttons, text="Сохранить", command=self.save)
        self.save_button.pack(side="right")
        # Снимок после заполнения исключает ложное предупреждение при открытии.
        self.initial_values = self.get_values()
        self.grab_set()
        self.entries["partner_name"].focus_set()

    @staticmethod
    def rating_allowed(value):
        return value == "" or (value.isascii() and value.isdigit() and len(value) <= 10 and int(value) <= 2147483647)

    def get_values(self):
        return {key: value.get() for key, value in self.values.items()}

    def save(self):
        if self.busy or self.closed:
            return
        try:
            values = validate_partner(self.get_values())
        except ValidationError as error:
            self.entries[error.field].focus_set()
            messagebox.showerror("Ошибка ввода", describe_error(error), parent=self)
            return
        self.set_busy(True)
        self.parent.save_card(self, values)

    def set_busy(self, busy):
        self.busy = busy
        for key, entry in self.entries.items():
            state = "readonly" if key == "partner_type" else "normal"
            entry.configure(state="disabled" if busy else state)
        self.back_button.configure(state="disabled" if busy else "normal")
        self.save_button.configure(state="disabled" if busy else "normal")
        self.status.set("Сохранение…" if busy else "Проверьте данные и повторите сохранение.")

    def on_escape(self, event=None):
        self.close()
        return "break"

    def close(self, saved=False):
        if self.closed or self.busy:
            return False
        if not saved and self.get_values() != self.initial_values:
            discard = messagebox.askyesno(
                "Несохранённые изменения",
                "Изменения будут потеряны без возможности восстановления. Выйти без сохранения?",
                icon="warning",
                parent=self,
            )
            if not discard:
                return False
        self.closed = True
        self.grab_release()
        self.destroy()
        self.parent.child_closed()
        return True
