import tkinter as tk
from decimal import Decimal, InvalidOperation
from tkinter import ttk

import theme
from dialogs import confirm_discard, show_error
from tooltip import ToolTip
from partner_validation import PartnerValidationError, partner_types, validate_partner


def prepare_form_values(partner=None):
    values = dict(partner or {})
    values.setdefault("rating", 0)
    if not values.get("partner_type"):
        # В старой БД тип записан в начале наименования, отдельного столбца нет.
        name = values.get("company_name") or ""
        prefix, separator, remainder = name.partition(" ")
        if separator and prefix in partner_types:
            values["partner_type"] = prefix
            values["company_name"] = remainder
    if values.get("partner_type") not in partner_types:
        values["partner_type"] = ""
    rating = values.get("rating")
    rating_hint = "Целое число от 0"
    if rating is not None and str(rating) != "":
        try:
            number = Decimal(str(rating))
            if not number.is_finite() or number < 0 or number != number.to_integral_value():
                raise ValueError
            values["rating"] = str(int(number))
        except (InvalidOperation, ValueError):
            # Дробный рейтинг старой БД нельзя незаметно округлять.
            values["rating"] = ""
    old_rating = (partner or {}).get("rating")
    if values.get("rating") == "" and old_rating is not None:
        rating_hint = f"В базе: {old_rating}. Укажите целое число от 0."
    return values, rating_hint


class PartnerEditWindow(tk.Toplevel):
    """Добавление или редактирование партнёра с сохранением в БД."""

    def __init__(self, parent, on_back, partner=None, icon_image=None, on_save=None):
        super().__init__(parent)
        self.withdraw()
        self.on_back = on_back
        self.on_save = on_save
        self.busy = False
        self.closed = False
        self.is_editing = partner is not None
        self.partner_id = None if partner is None else partner["partner_id"]
        self.values = {}
        self.entries = {}
        self.tooltips = {}
        mode = "Редактирование" if self.is_editing else "Добавление"
        self.title(f"CRM: Карточка партнера [{mode}]")
        self.configure(bg=theme.background)
        self.geometry("720x710")
        self.minsize(660, 680)
        self.transient(parent)
        self.icon_image = icon_image
        if icon_image is not None:
            self.iconphoto(False, icon_image)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", self.on_escape)
        initial_values, self.rating_hint = prepare_form_values(partner)
        self.build_form(initial_values)
        # Снимок делаем после заполнения: загрузка данных из БД не считается правкой.
        self.initial_values = self.get_values()
        self.update_idletasks()
        left = max(0, parent.winfo_rootx() + (parent.winfo_width() - 720) // 2)
        top = max(0, min(parent.winfo_rooty() + 45, self.winfo_screenheight() - 760))
        self.geometry(f"+{left}+{top}")
        self.deiconify()
        self.grab_set()
        self.focus_form()

    def build_form(self, initial_values):
        container = tk.Frame(self, bg=theme.background)
        container.pack(fill="both", expand=True, padx=26, pady=24)
        container.columnconfigure(1, weight=1)
        heading = "Редактирование партнёра" if self.is_editing else "Новый партнёр"
        tk.Label(
            container, text=heading, font=theme.heading_font,
            bg=theme.background, fg=theme.foreground, anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))
        description = "Данные нового партнёра"
        if self.is_editing:
            description = f"Карточка партнёра № {self.partner_id}"
        tk.Label(
            container, text=description, font=theme.body_font,
            bg=theme.background, fg=theme.muted, anchor="w",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 24))

        fields = [
            ("company_name", "Наименование"),
            ("partner_type", "Тип партнёра"),
            ("rating", "Рейтинг"),
            ("address", "Адрес"),
            ("director_name", "ФИО директора"),
            ("phone", "Телефон"),
            ("contact_email", "Email компании"),
            ("inn", "ИНН"),
        ]
        hints = {
            "rating": self.rating_hint,
            "phone": "Пример: +7 (999) 123-45-67",
            "contact_email": "Пример: partner@example.ru",
        }
        for row, (key, label) in enumerate(fields, start=2):
            tk.Label(
                container, text=label, font=theme.body_font,
                bg=theme.background, fg=theme.foreground, anchor="w",
            ).grid(row=row, column=0, sticky="nw", padx=(0, 18), pady=(13, 6))
            initial_value = initial_values.get(key)
            value = "" if initial_value is None else str(initial_value)
            self.values[key] = tk.StringVar(master=self, value=value)
            field_frame = tk.Frame(container, bg=theme.background)
            field_frame.grid(row=row, column=1, sticky="ew", pady=6)
            if key == "partner_type":
                # readonly разрешает выбор из списка и запрещает произвольный тип.
                entry = ttk.Combobox(
                    field_frame, textvariable=self.values[key], values=partner_types,
                    state="readonly", font=theme.body_font,
                )
                entry.pack(fill="x", ipady=5)
            else:
                entry = tk.Entry(
                    field_frame, textvariable=self.values[key], font=theme.body_font,
                    bg=theme.background, fg=theme.foreground, relief="solid", bd=1,
                )
                entry.pack(fill="x", ipady=5)
            if key in hints:
                tk.Label(
                    field_frame, text=hints[key], font=(theme.font_family, 10),
                    bg=theme.background, fg=theme.muted, anchor="w",
                ).pack(fill="x", pady=(3, 0))
            if key in ("phone", "contact_email"):
                self.tooltips[key] = ToolTip(entry, hints[key])
            self.entries[key] = entry

        self.message = tk.StringVar(master=self, value="Изменения будут записаны в БД после нажатия «Сохранить».")
        tk.Label(
            container,
            textvariable=self.message,
            font=theme.body_font, bg=theme.background, fg=theme.muted,
            wraplength=640, justify="left", anchor="w",
        ).grid(row=10, column=0, columnspan=2, sticky="w", pady=(12, 8))
        container.rowconfigure(11, weight=1)
        buttons = tk.Frame(container, bg=theme.background)
        buttons.grid(row=12, column=0, columnspan=2, sticky="e", pady=(8, 0))
        self.back_button = tk.Button(
            buttons, text="Назад", command=self.close, font=theme.body_font,
            bg=theme.button_background, fg=theme.foreground,
            activebackground=theme.button_hover, activeforeground=theme.foreground,
            relief="solid", bd=1, padx=22, pady=8, cursor="hand2",
        )
        self.back_button.pack(side="left", padx=(0, 12))
        self.save_button = tk.Button(
            buttons, text="Сохранить", command=self.save, font=theme.body_font,
            bg=theme.button_background, fg=theme.foreground,
            activebackground=theme.button_hover, activeforeground=theme.foreground,
            relief="solid", bd=1, padx=22, pady=8, cursor="hand2",
        )
        self.save_button.pack(side="left")

    def save(self):
        if self.closed or self.busy:
            return
        values = self.get_values()
        try:
            validated = validate_partner(values)
        except PartnerValidationError as error:
            self.show_error("Ошибка ввода", str(error))
            return
        if self.on_save is not None:
            self.on_save(validated, self.partner_id)

    def get_values(self):
        return {key: value.get() for key, value in self.values.items()}

    def has_changes(self):
        return self.get_values() != self.initial_values

    def show_error(self, title, message):
        self.message.set(message)
        for tooltip in self.tooltips.values():
            tooltip.hide()
        show_error(self, title, message)

    def set_busy(self, busy):
        self.busy = busy
        for key, entry in self.entries.items():
            state = "readonly" if key == "partner_type" else "normal"
            entry.configure(state="disabled" if busy else state)
        self.save_button.configure(state="disabled" if busy else "normal")
        self.back_button.configure(state="disabled" if busy else "normal")
        if busy:
            self.message.set("Сохранение… Дождитесь ответа базы данных.")

    def focus_form(self):
        if self.closed:
            return
        self.lift()
        self.entries["company_name"].focus_set()

    def on_escape(self, event=None):
        self.close()
        return "break"

    def close(self, notify=True, confirm=True):
        if self.closed or self.busy:
            return False
        if confirm and self.has_changes() and not confirm_discard(self):
            return False
        values = self.get_values()
        self.closed = True
        for tooltip in self.tooltips.values():
            tooltip.hide()
        if self.grab_current() == self:
            self.grab_release()
        self.destroy()
        if notify:
            self.on_back(values)
        return True
