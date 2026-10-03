import tkinter as tk

import theme
from main_window import MainWindow as PreviousMainWindow
from partner_history_service import load_partner_history
from partner_history_window import PartnerHistoryWindow


class MainWindow(PreviousMainWindow):
    def __init__(self, root, load_partners, *args, read_history=load_partner_history, **kwargs):
        self.read_history = read_history
        self.history_window = None
        self.selected_partner_id = None
        self.partner_cards = {}
        super().__init__(root, load_partners, *args, **kwargs)

    def build_layout(self):
        super().build_layout()
        history_actions = tk.Frame(self.root, bg=theme.background)
        history_actions.pack(fill="x", padx=26, pady=(12, 0), after=self.add_partner_button.master)
        self.history_button = self.make_button(history_actions, "История продаж", self.open_partner_history)
        self.history_button.pack(side="right")
        self.history_button.configure(state="disabled")
        self.selection_text = tk.StringVar(master=self.root, value="Выберите партнёра одним щелчком")
        self.make_label(history_actions, "", textvariable=self.selection_text,
                        wraplength=400, justify="left").pack(side="left", fill="x", expand=True, padx=(0, 12))

    def add_card(self, partner):
        super().add_card(partner)
        card = self.cards[-1]
        partner_id = partner["partner_id"]
        self.partner_cards[partner_id] = (card, partner)
        card.configure(takefocus=True)
        for widget in [card, *card.winfo_children()]:
            widget.bind("<Button-1>", lambda event, key=partner_id: self.select_partner(key), add="+")
        card.bind("<Return>", lambda event: self.select_partner(partner_id))
        card.bind("<space>", lambda event: self.select_partner(partner_id))

    def clear_cards(self):
        super().clear_cards()
        self.partner_cards.clear()
        self.update_history_button()

    def render_partners(self):
        super().render_partners()
        if not self.loading and self.selected_partner_id not in self.partner_cards:
            self.selected_partner_id = None
        self.update_history_button()

    def select_partner(self, partner_id):
        if self.closed or self.loading or self.history_is_open() or self.editor_is_open():
            return
        if partner_id in self.partner_cards:
            self.selected_partner_id = partner_id
            self.update_history_button()

    def update_history_button(self):
        if self.closed:
            return
        selected = self.partner_cards.get(self.selected_partner_id)
        enabled = selected is not None and not self.loading and self.password is not None
        self.history_button.configure(state="normal" if enabled else "disabled")
        for key, (card, partner) in self.partner_cards.items():
            color = theme.foreground if key == self.selected_partner_id else theme.border
            card.configure(highlightbackground=color, highlightcolor=color,
                           highlightthickness=2 if key == self.selected_partner_id else 1)
        self.selection_text.set(f"Выбран: {selected[1]['company_name']}" if selected else "Выберите партнёра одним щелчком")

    def set_main_busy(self, busy):
        super().set_main_busy(busy)
        self.update_history_button()

    def history_is_open(self):
        return self.history_window is not None and self.history_window.winfo_exists()

    def open_partner_history(self):
        if self.closed or self.loading or self.editor_is_open():
            return
        if self.history_is_open():
            self.history_window.focus_window()
            return
        selected = self.partner_cards.get(self.selected_partner_id)
        if selected is None or self.password is None:
            return
        partner = selected[1]
        password = self.password

        def return_to_main():
            self.history_window = None
            if not self.closed:
                self.root.lift()
                self.history_button.focus_set()

        name = " ".join(filter(None, (partner.get("partner_type"), partner["company_name"])))
        # В окно передаётся ID; история всегда читается заново из PostgreSQL.
        self.history_window = PartnerHistoryWindow(
            self.root, partner_id=partner["partner_id"], partner_name=name,
            load_history=lambda partner_id: self.read_history(password, partner_id),
            on_back=return_to_main, logo_image=self.logo_image, icon_image=self.icon_image,
        )

    def open_partner_editor(self, partner=None):
        if self.history_is_open():
            self.history_window.focus_window()
            return
        super().open_partner_editor(partner)

    def connect(self):
        if self.history_is_open():
            self.history_window.focus_window()
            return
        super().connect()

    def refresh(self):
        if self.closed or self.history_is_open():
            return
        super().refresh()
        self.update_history_button()

    def close(self):
        if self.history_is_open():
            self.history_window.close(notify=False)
            self.history_window = None
        super().close()
