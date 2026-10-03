import tkinter as tk

import theme
from history_main_window import MainWindow as HistoryMainWindow
from material_window import MaterialWindow


class MainWindow(HistoryMainWindow):
    def __init__(self, *args, **kwargs):
        self.material_window = None
        super().__init__(*args, **kwargs)

    def build_layout(self):
        super().build_layout()
        actions = tk.Frame(self.root, bg=theme.background)
        actions.pack(fill="x", padx=26, pady=(12, 0), after=self.history_button.master)
        self.material_button = self.make_button(actions, "Расчёт сырья", self.open_material_calculator)
        self.material_button.pack(side="right")
        self.make_label(actions, "Расход материалов для производства",
                        wraplength=340, justify="left").pack(side="left", padx=(0, 12))

    def material_is_open(self):
        return self.material_window is not None and self.material_window.winfo_exists()

    def focus_material_if_open(self):
        if not self.material_is_open():
            return False
        self.material_window.focus_window()
        return True

    def open_material_calculator(self):
        if self.closed or self.loading:
            return
        if self.focus_material_if_open():
            return
        if self.editor_is_open():
            self.edit_window.lift()
            return
        if self.history_is_open():
            self.history_window.focus_window()
            return
        if self.login_dialog is not None and self.login_dialog.winfo_exists():
            self.login_dialog.lift()
            return
        self.material_window = MaterialWindow(
            self.root, self.logo_image, self.icon_image, self.return_from_materials,
        )

    def return_from_materials(self):
        self.material_window = None
        if not self.closed:
            self.root.lift()
            self.material_button.focus_set()

    def open_partner_editor(self, partner=None):
        if not self.focus_material_if_open():
            super().open_partner_editor(partner)

    def open_partner_history(self):
        if not self.focus_material_if_open():
            super().open_partner_history()

    def select_partner(self, partner_id):
        if not self.focus_material_if_open():
            super().select_partner(partner_id)

    def connect(self):
        if not self.focus_material_if_open():
            super().connect()

    def refresh(self):
        if not self.focus_material_if_open():
            super().refresh()

    def close(self):
        if self.material_is_open():
            self.material_window.close(notify=False)
            self.material_window = None
        super().close()
