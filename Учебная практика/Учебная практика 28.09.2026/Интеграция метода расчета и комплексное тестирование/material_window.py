import tkinter as tk
from tkinter import ttk

import material_reference_data
import theme
from app_logging import log_error, log_validation
from dialogs import show_error
from material_calculator import calculate_material_quantity


class MaterialWindow(tk.Toplevel):
    def __init__(self, parent, logo_image, icon_image, on_back,
                 calculator=calculate_material_quantity):
        super().__init__(parent)
        self.withdraw()
        self.logo_image = logo_image
        self.icon_image = icon_image
        self.on_back = on_back
        self.calculator = calculator
        self.closed = False
        self.values = {}
        self.entries = {}
        self.title("CRM: Расчёт сырья для производства")
        self.configure(bg=theme.background)
        self.geometry("720x650")
        self.minsize(680, 650)
        self.transient(parent)
        self.iconphoto(False, self.icon_image)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.bind("<Escape>", self.on_escape)
        self.build_layout()
        for value in self.values.values():
            value.trace_add("write", self.invalidate_result)
        self.deiconify()
        self.grab_set()
        self.entries["quantity"].focus_set()

    def make_label(self, parent, text, **kwargs):
        return tk.Label(parent, text=text, bg=theme.background, fg=theme.foreground,
                        font=theme.body_font, anchor="w", **kwargs)

    def make_button(self, parent, text, command):
        return tk.Button(parent, text=text, command=command, font=theme.body_font,
                         bg=theme.button_background, fg=theme.foreground,
                         activebackground=theme.button_hover, relief="solid", bd=1,
                         padx=16, pady=7, cursor="hand2")

    def build_layout(self):
        header = tk.Frame(self, bg=theme.background)
        header.pack(fill="x", padx=26, pady=(24, 16))
        tk.Label(header, image=self.logo_image, bg=theme.background).pack(side="left")
        tk.Label(header, text="Расчёт сырья", font=theme.heading_font,
                 bg=theme.background, fg=theme.foreground).pack(side="left", padx=16)
        self.make_label(self, "Учебные справочники: коэффициенты и процент брака заданы для проверки.",
                        wraplength=610, justify="left").pack(fill="x", padx=26, pady=(0, 14))

        buttons = tk.Frame(self, bg=theme.background)
        buttons.pack(side="bottom", fill="x", padx=26, pady=18)
        self.back_button = self.make_button(buttons, "Назад", self.close)
        self.back_button.pack(side="right")
        self.calculate_button = self.make_button(buttons, "Рассчитать", self.calculate)
        self.calculate_button.pack(side="right", padx=(0, 12))

        form = tk.Frame(self, bg=theme.background)
        form.pack(fill="x", padx=26)
        form.columnconfigure(1, weight=1)
        product_hint = ";  ".join(
            f"{key} → коэффициент {value}" for key, value in material_reference_data.product_type_coefficients.items()
        )
        material_hint = ";  ".join(
            f"{key} → брак {value}%" for key, value in material_reference_data.material_defect_percentages.items()
        )
        self.add_field(form, 0, "product_type_id", "ID типа продукции", product_hint,
                       material_reference_data.product_type_coefficients)
        self.add_field(form, 1, "material_type_id", "ID типа материала", material_hint,
                       material_reference_data.material_defect_percentages)
        self.add_field(form, 2, "quantity", "Количество продукции", "Целое число больше нуля. Например: 10")
        self.add_field(form, 3, "param_1", "Параметр 1", "Положительное число. Например: 2 или 2,5")
        self.add_field(form, 4, "param_2", "Параметр 2", "Положительное число. Например: 3 или 3.5")

        self.result_text = tk.StringVar(master=self, value="Заполните параметры и нажмите «Рассчитать».")
        self.result_label = tk.Label(
            self, textvariable=self.result_text, font=theme.card_title_font,
            bg=theme.button_background, fg=theme.foreground, anchor="w", justify="left",
            wraplength=600, padx=14, pady=14, relief="solid", bd=1,
        )
        self.result_label.pack(fill="x", padx=26, pady=(16, 0))

    def add_field(self, form, row, key, title, hint, choices=None):
        value = tk.StringVar(master=self, value="")
        self.values[key] = value
        self.make_label(form, title).grid(row=row * 2, column=0, sticky="w", padx=(0, 14))
        if choices is None:
            entry = tk.Entry(form, textvariable=value, font=theme.body_font,
                             bg=theme.background, fg=theme.foreground, relief="solid", bd=1)
        else:
            entry = ttk.Combobox(form, textvariable=value, values=tuple(str(key) for key in choices),
                                 font=theme.body_font)
            value.set(str(next(iter(choices))))
        self.entries[key] = entry
        entry.grid(row=row * 2, column=1, sticky="ew", ipady=4)
        entry.bind("<Return>", self.on_calculate)
        self.make_label(form, hint, wraplength=610, justify="left").grid(
            row=row * 2 + 1, column=0, columnspan=2, sticky="w", pady=(4, 12),
        )

    def invalidate_result(self, *args):
        self.result_text.set("Параметры изменены. Нажмите «Рассчитать».")

    def calculate(self):
        if self.closed:
            return
        self.result_text.set("Расчёт не выполнен.")
        try:
            product_type_id = int(self.values["product_type_id"].get().strip())
            material_type_id = int(self.values["material_type_id"].get().strip())
            quantity = int(self.values["quantity"].get().strip())
            param_1 = float(self.values["param_1"].get().strip().replace(",", "."))
            param_2 = float(self.values["param_2"].get().strip().replace(",", "."))
            result = self.calculator(product_type_id, material_type_id, quantity, param_1, param_2)
            if result == -1:
                log_validation("Расчёт сырья", "Метод вернул -1: неизвестный тип или недопустимые параметры.")
                self.show_input_error()
                return
            self.result_text.set(f"Необходимое количество сырья: {result}")
        except (ValueError, TypeError, ArithmeticError) as error:
            log_error("Расчёт сырья", error, "Неверный формат чисел. Проверьте ID, количество и параметры продукции.")
            self.show_input_error()
        except Exception as error:
            log_error("Расчёт сырья", error, "Непредвиденная ошибка метода расчёта.")
            show_error(self, "Ошибка расчёта сырья",
                       "Расчёт временно недоступен. Повторите попытку. "
                       "Если ошибка повторяется, передайте журнал app.log для проверки.")

    def show_input_error(self):
        show_error(
            self, "Ошибка расчёта сырья",
            "Не удалось рассчитать расход сырья.\n\n"
            "1. Выберите существующие ID типов из выпадающих списков.\n"
            "2. Введите количество продукции — целое число больше нуля.\n"
            "3. Введите оба параметра — положительные конечные числа. "
            "Допускается точка или запятая.\n\n"
            "Исправьте значения и нажмите «Рассчитать». Введённые данные сохранены в форме.",
        )

    def on_calculate(self, event=None):
        self.calculate()
        return "break"

    def focus_window(self):
        if not self.closed:
            self.lift()
            self.calculate_button.focus_set()

    def on_escape(self, event=None):
        self.close()
        return "break"

    def close(self, notify=True):
        if self.closed:
            return
        self.closed = True
        if self.grab_current() == self:
            self.grab_release()
        self.destroy()
        if notify:
            self.on_back()
